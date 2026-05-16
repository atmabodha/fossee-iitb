"""
Sequencing Engine — core algorithm logic (V3.3).

Determines the next question to serve to a student based on their
current learning state, following the deterministic sequencing rules
from the algorithm specification.
"""

from __future__ import annotations

import hashlib
import logging
import random
from typing import List

from api_architecture.models.question import Question
from api_architecture.models.student_state import StudentState
from api_architecture.utils.constants import (
    MASTERY_STREAK,
    MIN_ATTEMPTS,
    RECENT_QUESTIONS_MAX,
    CONCEPT_PROGRESSION,
    get_priority_order,
)

logger = logging.getLogger(__name__)


class QuestionBankExhaustedError(Exception):
    """Raised when no questions are available for the concept."""


class ConceptMastered:
    """Sentinel value returned when the current concept is mastered."""

    pass


CONCEPT_MASTERED = ConceptMastered()


# ---------------------------------------------------------------------------
# Deterministic seed derivation for Random Mode
# ---------------------------------------------------------------------------

def _derive_seed(state: StudentState) -> int:
    """Produce a deterministic seed from stable student state inputs.

    seed = SHA-256(student_id | current_concept | attempts | last_question_id)
    """
    parts = [
        str(state.student_id),
        state.current_concept,
        str(state.attempts_in_concept),
        str(state.last_question_id or ""),
    ]
    raw = "|".join(parts).encode()
    digest = hashlib.sha256(raw).hexdigest()
    return int(digest[:16], 16)  # 64-bit integer from first 16 hex chars


# ---------------------------------------------------------------------------
# Main sequencing function
# ---------------------------------------------------------------------------

async def sequence_next_question(
    state: StudentState,
    question_fetcher,
) -> Question:
    """Determine and return the next question for the student.

    Parameters
    ----------
    state : StudentState
        Mutable student state — updated in-place.
    question_fetcher : object
        Must expose:
          - fetch(concept, error_type, exclude_ids) -> List[Question]
          - fetch_any(concept, exclude_ids) -> List[Question]

    Returns
    -------
    Question
        The selected question.

    Raises
    ------
    QuestionBankExhaustedError
        If no question can be found for the concept.
    """
    priority_order = get_priority_order(state.current_concept)

    # --- Random mode activation -------------------------------------------
    _apply_random_mode_if_needed(state)

    # --- Error-type selection ---------------------------------------------
    target_error_type = _choose_target_error_type(state, priority_order)

    # --- Question retrieval (4-step fallback) -----------------------------
    question = await _retrieve_question(state, target_error_type, question_fetcher)

    # --- Post-selection bookkeeping ---------------------------------------
    _post_selection_bookkeeping(state, question, target_error_type)

    return question


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

class MasterySignal(Exception):
    """Signal raised when the engine determines the concept is mastered.

    This was previously an internal-only name (_MasterySignal). Exposing a
    public name makes it safe for tests and the service layer to import it
    without accessing a protected member.
    """

    pass


def _apply_random_mode_if_needed(state: StudentState) -> None:
    """Activate Random Mode when attempts >= MIN_ATTEMPTS and streak below mastery."""
    if state.attempts_in_concept >= MIN_ATTEMPTS and state.current_streak < MASTERY_STREAK:
        if not state.in_random_mode:
            logger.info(
                "Student %s entering Random Mode for concept %s",
                state.student_id,
                state.current_concept,
            )
        state.in_random_mode = True
        state.forced_resolve_active = False  # ignored in Random Mode

def _choose_target_error_type(state: StudentState, priority_order: List[str]) -> str:
    """Return target error type according to mode."""
    if state.in_random_mode:
        return _select_random_error_type(state, priority_order)
    return _select_sequential_error_type(state, priority_order)

def _post_selection_bookkeeping(state: StudentState, question: Question, target_error_type: str) -> None:
    """Handle state updates after a question is selected."""
    qid_str = str(question.question_id)
    actual_error_type = question.error_type or target_error_type
    state.last_error_type = actual_error_type

    state.last_question_id = question.question_id
    state.recent_question_ids = (state.recent_question_ids + [qid_str])[
        -RECENT_QUESTIONS_MAX:
    ]

    is_new = qid_str not in state.presented_question_ids
    if is_new:
        # If we're in forced-resolve mode (student made a mistake or used a hint),
        # retries should not count as new attempts. Still record the question as
        # presented so it won't be double-counted later.
        if not state.forced_resolve_active:
            state.attempts_in_concept += 1
            logger.debug("New question %s served (attempt %d)", qid_str, state.attempts_in_concept)
        else:
            logger.debug("Forced-resolve retry served (not counted as attempt): %s", qid_str)

        state.presented_question_ids = state.presented_question_ids + [qid_str]
    state.last_question_was_new = is_new

def _mark_mastery(state: StudentState) -> None:
    """Update state fields for mastery and unlock next concept."""
    concept = state.current_concept
    if concept not in state.mastered_concepts:
        state.mastered_concepts = state.mastered_concepts + [concept]
    logger.info("Student %s mastered concept %s", state.student_id, concept)

    # Unlock next concept
    idx = CONCEPT_PROGRESSION.index(concept) if concept in CONCEPT_PROGRESSION else -1
    if idx >= 0 and idx + 1 < len(CONCEPT_PROGRESSION):
        next_concept = CONCEPT_PROGRESSION[idx + 1]
        if next_concept not in state.unlocked_concepts:
            state.unlocked_concepts = state.unlocked_concepts + [next_concept]
            logger.info("Concept %s unlocked for student %s", next_concept, state.student_id)

    # Advance to next concept & reset state
    if idx >= 0 and idx + 1 < len(CONCEPT_PROGRESSION):
        state.current_concept = CONCEPT_PROGRESSION[idx + 1]
    state.attempts_in_concept = 0
    state.current_streak = 0
    state.current_error_type_index = 0
    state.in_random_mode = False
    state.forced_resolve_active = False
    state.last_question_was_new = False
    state.recent_question_ids = []
    state.presented_question_ids = []


def _select_random_error_type(
    state: StudentState,
    priority_order: List[str],
) -> str:
    """Randomly pick an error type, avoiding the last one served."""
    seed = _derive_seed(state)
    rng = random.Random(seed)
    logger.debug("Random mode seed=%d for student %s", seed, state.student_id)

    available = [
        et for et in priority_order if et != state.last_error_type
    ]
    if not available:
        available = list(priority_order)
    return rng.choice(available)


def _select_sequential_error_type(
    state: StudentState,
    priority_order: List[str],
) -> str:
    """Deterministically pick the next error type in priority order."""
    if state.forced_resolve_active:
        target_index = state.current_error_type_index
    elif state.attempts_in_concept == 0:
        target_index = 0
    elif state.last_answer_correct and not state.last_hint_used:
        next_index = state.current_error_type_index + 1
        if next_index >= len(priority_order):
            next_index = 0  # loop back to Syntax
        target_index = next_index
    else:
        target_index = state.current_error_type_index

    state.current_error_type_index = target_index
    return priority_order[target_index]


async def _retrieve_question(
    state: StudentState,
    target_error_type: str,
    _fetcher,
) -> Question:
    """4-step exhaustion fallback per the spec.
    
    When forced_resolve_active=True, prioritizes serving the same question
    that triggered the error (to allow students to retry and fix their mistake).
    """
    # Forced-resolve priority: retry the exact same question
    if state.forced_resolve_active and state.last_question_id:
        question = await _fetcher.fetch_by_id(state.last_question_id)
        if question and question.concept == state.current_concept:
            logger.debug(
                "Forced-resolve: retrying question %s for concept %s",
                state.last_question_id,
                state.current_concept,
            )
            return question
        # If last question no longer available or wrong concept, fall through to normal flow
    
    # Step 1 — normal fetch
    pool = await _fetcher.fetch(
        state.current_concept, target_error_type, state.recent_question_ids
    )
    if pool:
        return _pick(pool, state)

    # Step 2 — reset exclusion, retry
    logger.debug("Resetting exclusion for error_type=%s", target_error_type)
    pool = await _fetcher.fetch(state.current_concept, target_error_type, [])
    if pool:
        return _pick(pool, state)

    # Step 3 — any question in concept
    logger.debug("Fallback: fetching any question in concept %s", state.current_concept)
    pool = await _fetcher.fetch_any(state.current_concept, state.recent_question_ids)
    if pool:
        return _pick(pool, state)

    # Step 4 — exhausted
    raise QuestionBankExhaustedError(
        f"No questions available for concept {state.current_concept}"
    )


def _pick(pool: List[Question], state: StudentState) -> Question:
    """Select one question from the pool using deterministic RNG."""
    if len(pool) == 1:
        return pool[0]
    seed = _derive_seed(state)
    rng = random.Random(seed)
    return rng.choice(pool)
