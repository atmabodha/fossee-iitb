"""
PostgreSQL storage for student states and question bank.

Replaces the in-memory dictionary-based storage with an async SQLAlchemy layer.
"""
from __future__ import annotations

import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime

from sqlalchemy import select, func, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from api_architecture.models.question import Question
from api_architecture.models.student_state import StudentState
from api_architecture.utils.constants import RECENT_QUESTIONS_MAX
from api_architecture.database.models import QuestionRecord, StudentStateRecord, UserRecord, OutputLogRecord, StudentSummaryRecord, SubmissionRecord, StudentConceptStatus, StudentQuestionHistory, StudentConceptStatus, StudentQuestionHistory

logger = logging.getLogger(__name__)

async def get_student_state(db: AsyncSession, student_id: uuid.UUID) -> Optional[StudentState]:
    result = await db.execute(select(StudentStateRecord).where(StudentStateRecord.student_id == student_id))
    record = result.scalars().first()
    if not record:
        return None
    
    summary_result = await db.execute(select(StudentSummaryRecord).where(StudentSummaryRecord.student_id == student_id))
    summary_record = summary_result.scalars().first()

    recent_ids = sorted([qh for qh in record.question_history if qh.is_recent], key=lambda x: x.order_index)
    presented_ids = sorted([qh for qh in record.question_history if qh.is_presented], key=lambda x: x.order_index)
    
    recent_question_ids = [qh.question_id for qh in recent_ids]
    presented_question_ids = [qh.question_id for qh in presented_ids]

    attempted_concepts = []
    mastered_concepts = []
    unlocked_concepts = []
    if summary_record and summary_record.concept_status:
        for cs in summary_record.concept_status:
            if cs.is_attempted: attempted_concepts.append(cs.concept)
            if cs.is_mastered: mastered_concepts.append(cs.concept)
            if cs.is_unlocked: unlocked_concepts.append(cs.concept)
    if not unlocked_concepts:
        unlocked_concepts = ["C1"]

    return StudentState(
        student_id=record.student_id,
        current_concept=record.current_concept,
        attempts_in_concept=record.attempts_in_concept,
        current_streak=record.current_streak,
        current_error_type_index=record.current_error_type_index,
        last_question_id=record.last_question_id,
        last_error_type=record.last_error_type,
        last_answer_correct=record.last_answer_correct,
        last_hint_used=record.last_hint_used,
        in_random_mode=record.in_random_mode,
        forced_resolve_active=record.forced_resolve_active,
        last_question_was_new=record.last_question_was_new,
        recent_question_ids=recent_question_ids,
        presented_question_ids=presented_question_ids,
        attempted_concepts=attempted_concepts,
        mastered_concepts=mastered_concepts,
        unlocked_concepts=unlocked_concepts,
        state_version=record.state_version
    )

async def create_student_profile(db: AsyncSession, student_id: uuid.UUID) -> StudentState:
    try:
        if isinstance(student_id, str):
            student_id = uuid.UUID(student_id)
    except ValueError:
        pass

    # Ensure a UserRecord exists
    user_res = await db.execute(select(UserRecord).where(UserRecord.student_id == student_id))
    if not user_res.scalars().first():
        u = UserRecord(student_id=student_id, username=f"User_{str(student_id)[:8]}", email=f"user_{str(student_id)[:8]}@example.com")
        db.add(u)
        await db.flush()

    record = StudentStateRecord(student_id=student_id)
    summary_record = StudentSummaryRecord(student_id=student_id)
    db.add(record)
    db.add(summary_record)
    await db.commit()
    await db.refresh(record)
    return await get_student_state(db, student_id)

async def save_student_state(db: AsyncSession, state: StudentState) -> None:
    if len(state.recent_question_ids) > RECENT_QUESTIONS_MAX:
        state.recent_question_ids = state.recent_question_ids[-RECENT_QUESTIONS_MAX:]

    state.state_version += 1
    
    # Update State Record
    result = await db.execute(select(StudentStateRecord).where(StudentStateRecord.student_id == state.student_id))
    record = result.scalars().first()
    if record:
        record.current_concept = state.current_concept
        record.attempts_in_concept = state.attempts_in_concept
        record.current_streak = state.current_streak
        record.current_error_type_index = state.current_error_type_index
        record.last_question_id = state.last_question_id
        record.last_error_type = state.last_error_type
        record.last_answer_correct = state.last_answer_correct
        record.last_hint_used = state.last_hint_used
        record.in_random_mode = state.in_random_mode
        record.forced_resolve_active = state.forced_resolve_active
        record.last_question_was_new = state.last_question_was_new
        record.state_version = state.state_version
        
        # Rebuild Question History
        await db.execute(delete(StudentQuestionHistory).where(StudentQuestionHistory.student_id == state.student_id))
        
        qh_records = []
        for i, qid in enumerate(state.recent_question_ids):
            qh_records.append(StudentQuestionHistory(student_id=state.student_id, question_id=str(qid), is_recent=True, is_presented=(qid in state.presented_question_ids), order_index=i))
            
        for i, qid in enumerate(state.presented_question_ids):
            if qid not in state.recent_question_ids:
                qh_records.append(StudentQuestionHistory(student_id=state.student_id, question_id=str(qid), is_recent=False, is_presented=True, order_index=i+1000))
                
        db.add_all(qh_records)

    # Update Summary Record
    summary_result = await db.execute(select(StudentSummaryRecord).where(StudentSummaryRecord.student_id == state.student_id))
    summary_record = summary_result.scalars().first()
    if summary_record:
        await db.execute(delete(StudentConceptStatus).where(StudentConceptStatus.student_id == state.student_id))
        
        all_concepts = set(state.attempted_concepts + state.mastered_concepts + state.unlocked_concepts)
        cs_records = []
        for c in all_concepts:
            cs_records.append(StudentConceptStatus(
                student_id=state.student_id,
                concept=c,
                is_attempted=(c in state.attempted_concepts),
                is_mastered=(c in state.mastered_concepts),
                is_unlocked=(c in state.unlocked_concepts)
            ))
        db.add_all(cs_records)
        
    await db.commit()

async def get_question_by_id(db: AsyncSession, question_id: uuid.UUID) -> Optional[Question]:
    result = await db.execute(select(QuestionRecord).where(QuestionRecord.question_id == question_id))
    record = result.scalars().first()
    if not record:
        return None
    return Question(
        question_id=record.question_id,
        concept=record.concept,
        error_type=record.error_type,
        question=record.question,
        solution=record.solution,
        test_cases=record.test_cases,
        language=record.language,
        metadata=record.metadata_json
    )

async def fetch_questions(
    db: AsyncSession,
    concept: str,
    error_type: str,
    exclude_ids: Optional[List[str]] = None,
) -> List[Question]:
    stmt = select(QuestionRecord).where(
        QuestionRecord.concept == concept,
        QuestionRecord.error_type == error_type
    )
    if exclude_ids:
        exclude_uuids = []
        for eid in exclude_ids:
            try:
                exclude_uuids.append(uuid.UUID(eid) if isinstance(eid, str) else eid)
            except ValueError:
                pass
        if exclude_uuids:
            stmt = stmt.where(QuestionRecord.question_id.not_in(exclude_uuids))

    result = await db.execute(stmt)
    records = result.scalars().all()
    return [
        Question(
            question_id=r.question_id,
            concept=r.concept,
            error_type=r.error_type,
            question=r.question,
            test_cases=r.test_cases,
            language=r.language,
            solution=r.solution,
            metadata=r.metadata_json
        ) for r in records
    ]

async def fetch_any_question_in_concept(
    db: AsyncSession,
    concept: str,
    exclude_ids: Optional[List[str]] = None,
) -> List[Question]:
    stmt = select(QuestionRecord).where(QuestionRecord.concept == concept)
    if exclude_ids:
        exclude_uuids = []
        for eid in exclude_ids:
            try:
                exclude_uuids.append(uuid.UUID(eid) if isinstance(eid, str) else eid)
            except ValueError:
                pass
        if exclude_uuids:
            stmt = stmt.where(QuestionRecord.question_id.not_in(exclude_uuids))

    result = await db.execute(stmt)
    records = result.scalars().all()
    return [
        Question(
            question_id=r.question_id,
            concept=r.concept,
            error_type=r.error_type,
            question=r.question,
            test_cases=r.test_cases,
            language=r.language,
            solution=r.solution,
            metadata=r.metadata_json
        ) for r in records
    ]

class AsyncQuestionFetcher:
    """Asynchronous question fetcher backed by PostgreSQL."""
    
    def __init__(self, db: AsyncSession):
        self.db = db

    async def fetch(
        self,
        concept: str,
        error_type: str,
        exclude_ids: Optional[List[str]] = None,
    ) -> List[Question]:
        return await fetch_questions(self.db, concept, error_type, exclude_ids)

    async def fetch_any(
        self,
        concept: str,
        exclude_ids: Optional[List[str]] = None,
    ) -> List[Question]:
        return await fetch_any_question_in_concept(self.db, concept, exclude_ids)

    async def fetch_by_id(self, question_id: uuid.UUID) -> Optional[Question]:
        return await get_question_by_id(self.db, question_id)

async def get_loaded_question_count(db: AsyncSession) -> int:
    result = await db.execute(select(func.count()).select_from(QuestionRecord))
    return result.scalar() or 0

async def log_interaction(
    db: AsyncSession,
    student_id: uuid.UUID,
    action_type: str,
    state: StudentState,
    question_id: Optional[uuid.UUID] = None,
    is_correct: Optional[bool] = None,
    hint_used: Optional[bool] = None
) -> None:
    try:
        if isinstance(student_id, str):
            student_id = uuid.UUID(student_id)
        if question_id and isinstance(question_id, str):
            question_id = uuid.UUID(question_id)
            
        record = OutputLogRecord(
            student_id=student_id,
            action_type=action_type,
            question_id=question_id,
            is_correct=is_correct,
            hint_used=hint_used,
            timestamp=datetime.utcnow().isoformat() + "Z",
            state_snapshot=state.model_dump()
        )
        db.add(record)
        await db.commit()
    except Exception as e:
        logger.exception("Failed to log interaction to db")

async def log_submission(
    db: AsyncSession,
    student_id: uuid.UUID,
    question_id: uuid.UUID,
    is_correct: bool,
    hint_used: bool,
    submitted_code: str,
    error_type: Optional[str],
    failed_test_cases: Optional[Any],
    ai_feedback: Optional[str],
    streak_at_submission: int,
) -> None:
    """Record a comprehensive history log of a student's submission."""
    try:
        if isinstance(student_id, str):
            student_id = uuid.UUID(student_id)
        if isinstance(question_id, str):
            question_id = uuid.UUID(question_id)

        record = SubmissionRecord(
            student_id=student_id,
            question_id=question_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
            is_correct=is_correct,
            hint_used=hint_used,
            submitted_code=submitted_code,
            error_type=error_type,
            failed_test_cases=failed_test_cases,
            ai_feedback=ai_feedback,
            streak_at_submission=streak_at_submission
        )
        db.add(record)
        await db.commit()
    except Exception as e:
        logger.exception("Failed to log submission to db")

async def clear_all(db: AsyncSession) -> None:
    """Clear all database tables."""
    await db.execute(delete(SubmissionRecord))
    await db.execute(delete(OutputLogRecord))
    await db.execute(delete(StudentStateRecord))
    await db.execute(delete(UserRecord))
    await db.execute(delete(QuestionRecord))
    await db.commit()

