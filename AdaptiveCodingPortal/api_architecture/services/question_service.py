from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from api_architecture.engine.sequencing_engine import (
    ConceptMastered,
    MasterySignal,
    QuestionBankExhaustedError,
    sequence_next_question,
)
from api_architecture.engine.submission_processor import SubmissionResult, process_submission
from api_architecture.services.storage import (
    AsyncQuestionFetcher,
    log_interaction,
    create_student_profile,
    get_question_by_id,
    get_student_state,
    save_student_state,
)
from api_architecture.utils.constants import CONCEPT_PROGRESSION
from api_architecture.models.student_state import StudentState

logger = logging.getLogger(__name__)

class StudentNotFoundError(Exception):
    pass

class InvalidSubmissionError(Exception):
    pass

class ConceptLockedError(Exception):
    pass

class InvalidConceptResetError(Exception):
    pass


# ---------------------------------------------------------------------------
# High-level service methods (Stateful)
# ---------------------------------------------------------------------------

async def get_next_question(db: AsyncSession, user_id: UUID) -> Dict[str, Any]:
    state = await get_student_state(db, user_id)
    if state is None:
        state = await create_student_profile(db, user_id)
    
    res, updated_state = await process_state_next_question(db, state)
    await save_student_state(db, updated_state)
    return res

async def submit_answer(
    db: AsyncSession,
    user_id: UUID,
    question_id: UUID,
    is_correct: bool,
    hint_used: bool,
) -> Optional[Dict[str, Any]]:
    state = await get_student_state(db, user_id)
    if state is None:
        raise StudentNotFoundError(f"Student {user_id} not found")
    
    res, updated_state = await process_state_submit_answer(db, state, question_id, is_correct, hint_used)
    await save_student_state(db, updated_state)
    return res

async def reset_concept(db: AsyncSession, user_id: UUID, concept_id: str) -> Dict[str, Any]:
    state = await get_student_state(db, user_id)
    if state is None:
        raise StudentNotFoundError(f"Student {user_id} not found")

    if concept_id not in CONCEPT_PROGRESSION:
        raise ValueError(f"Unknown concept: {concept_id}")

    state.current_concept = concept_id
    state.attempts_in_concept = 0
    state.current_streak = 0
    state.current_error_type_index = 0
    state.last_question_id = None

    if concept_id not in state.unlocked_concepts:
        state.unlocked_concepts.append(concept_id)

    if concept_id in state.mastered_concepts:
        state.mastered_concepts = [c for c in state.mastered_concepts if c != concept_id]

    await save_student_state(db, state)
    return {"status": "ok", "concept_reset": concept_id, "updated_state": state.model_dump()}


# ---------------------------------------------------------------------------
# Stateless processing methods
# ---------------------------------------------------------------------------

async def process_state_next_question(db: AsyncSession, state: StudentState) -> Tuple[Dict[str, Any], StudentState]:
    _ensure_current_concept_unlocked(state)
    _mark_attempted_concept(state)

    _fetcher = AsyncQuestionFetcher(db)
    try:
        question = await sequence_next_question(state, _fetcher)
    except MasterySignal:
        await log_interaction(db, state.student_id, "mastery_reached", state)
        return _make_mastery_response(state), state

    await log_interaction(db, state.student_id, "next_question", state, question_id=question.question_id)
    return _make_question_response(question, state), state

async def process_state_submit_answer(
    db: AsyncSession,
    state: StudentState,
    question_id: UUID,
    is_correct: bool,
    hint_used: bool,
) -> Tuple[Dict[str, Any], StudentState]:
    _ensure_current_concept_unlocked(state)
    await _validate_submission(db, state, question_id)

    result = SubmissionResult(is_correct=is_correct, hint_used=hint_used)
    mastery = process_submission(state, result)

    await log_interaction(db, state.student_id, "submit_answer", state, question_id=question_id, is_correct=is_correct, hint_used=hint_used)
    return _make_submission_response(mastery, state), state


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _make_mastery_response(state) -> Dict[str, Any]:
    return {
        "concept_mastered": True,
        "mastered_concept": (state.mastered_concepts[-1] if state.mastered_concepts else None),
        "current_concept": state.current_concept,
        "attempts": state.attempts_in_concept,
        "current_streak": state.current_streak,
        "updated_state": state.model_dump(),
        "metadata": {
            "in_random_mode": state.in_random_mode,
            "forced_resolve_active": state.forced_resolve_active,
            "last_question_was_new": state.last_question_was_new,
            "last_error_type": state.last_error_type,
            "current_error_type_index": state.current_error_type_index,
        },
    }

def _make_question_response(question, state) -> Dict[str, Any]:
    return {
        "question_id": str(question.question_id),
        "concept": question.concept,
        "error_type": question.error_type,
        "attempts": state.attempts_in_concept,
        "current_streak": state.current_streak,
        "updated_state": state.model_dump(),
        "metadata": {
            "in_random_mode": state.in_random_mode,
            "forced_resolve_active": state.forced_resolve_active,
            "last_question_was_new": state.last_question_was_new,
            "last_error_type": state.last_error_type,
            "current_error_type_index": state.current_error_type_index,
            "recent_question_ids": list(state.recent_question_ids),
            "presented_question_ids": list(state.presented_question_ids),
        },
    }

def _make_submission_response(mastery, state) -> Dict[str, Any]:
    return {
        "concept_mastered": mastery == "CONCEPT_MASTERED",
        "current_streak": state.current_streak,
        "attempts": state.attempts_in_concept,
        "last_answer_correct": state.last_answer_correct,
        "last_hint_used": state.last_hint_used,
        "updated_state": state.model_dump(),
        "metadata": {
            "in_random_mode": state.in_random_mode,
            "forced_resolve_active": state.forced_resolve_active,
            "last_question_was_new": state.last_question_was_new,
        },
    }

def _ensure_current_concept_unlocked(state) -> None:
    if state.current_concept not in state.unlocked_concepts:
        raise ConceptLockedError(
            f"Concept {state.current_concept} is locked for student {state.student_id}"
        )

def _mark_attempted_concept(state) -> None:
    if state.current_concept not in state.attempted_concepts:
        state.attempted_concepts = state.attempted_concepts + [state.current_concept]

async def _validate_submission(db: AsyncSession, state, question_id: UUID) -> None:
    active_question = state.last_question_id
    if active_question is None:
        raise InvalidSubmissionError("No active question to submit")
    if active_question != question_id:
        raise InvalidSubmissionError("Submitted question does not match active question")

    question = await get_question_by_id(db, question_id)
    if question is None:
        raise InvalidSubmissionError("Submitted question was not found")
    if question.concept != state.current_concept:
        raise InvalidSubmissionError("Submitted question does not belong to current concept")

