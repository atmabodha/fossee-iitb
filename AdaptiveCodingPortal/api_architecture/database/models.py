import uuid
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import relationship
from .db import Base

class UserRecord(Base):
    __tablename__ = "users"

    student_id = Column(UUID(as_uuid=True), primary_key=True)
    username = Column(String, nullable=False)
    email = Column(String, nullable=False)

class OutputLogRecord(Base):
    __tablename__ = "output_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.student_id"), nullable=False)
    action_type = Column(String, nullable=False)
    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.question_id"), nullable=True)
    is_correct = Column(Boolean, nullable=True)
    hint_used = Column(Boolean, nullable=True)
    timestamp = Column(String, nullable=False)
    state_snapshot = Column(JSONB, nullable=True)

class QuestionRecord(Base):
    __tablename__ = "questions"

    question_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    concept = Column(String, nullable=False, index=True)
    error_type = Column(String, nullable=False, index=True)
    question = Column(String, nullable=False, default="")
    solution = Column(String, nullable=True)
    test_cases = Column(JSONB, nullable=True)
    language = Column(String, nullable=False, default="python")
    metadata_json = Column(JSONB, nullable=True)

class StudentConceptStatus(Base):
    __tablename__ = "student_concept_status"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("student_summaries.student_id", ondelete="CASCADE"), nullable=False, index=True)
    concept = Column(String, nullable=False, index=True)
    is_attempted = Column(Boolean, nullable=False, default=False)
    is_mastered = Column(Boolean, nullable=False, default=False)
    is_unlocked = Column(Boolean, nullable=False, default=False)

    summary = relationship("StudentSummaryRecord", back_populates="concept_status")

class StudentQuestionHistory(Base):
    __tablename__ = "student_question_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("student_states.student_id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(String, nullable=False, index=True)
    is_recent = Column(Boolean, nullable=False, default=False)
    is_presented = Column(Boolean, nullable=False, default=False)
    order_index = Column(Integer, nullable=False, default=0)

    state = relationship("StudentStateRecord", back_populates="question_history")

class StudentStateRecord(Base):
    __tablename__ = "student_states"

    student_id = Column(UUID(as_uuid=True), ForeignKey("users.student_id"), primary_key=True)
    current_concept = Column(String, nullable=False, default="C1")
    attempts_in_concept = Column(Integer, nullable=False, default=0)
    current_streak = Column(Integer, nullable=False, default=0)
    current_error_type_index = Column(Integer, nullable=False, default=0)

    last_question_id = Column(UUID(as_uuid=True), ForeignKey("questions.question_id"), nullable=True)
    last_error_type = Column(String, nullable=True)
    last_answer_correct = Column(Boolean, nullable=True)
    last_hint_used = Column(Boolean, nullable=True)

    in_random_mode = Column(Boolean, nullable=False, default=False)
    forced_resolve_active = Column(Boolean, nullable=False, default=False)
    last_question_was_new = Column(Boolean, nullable=False, default=False)

    question_history = relationship("StudentQuestionHistory", back_populates="state", cascade="all, delete-orphan", lazy="selectin")
    
    state_version = Column(Integer, nullable=False, default=0)

class StudentSummaryRecord(Base):
    __tablename__ = "student_summaries"

    student_id = Column(UUID(as_uuid=True), ForeignKey("users.student_id"), primary_key=True)
    concept_status = relationship("StudentConceptStatus", back_populates="summary", cascade="all, delete-orphan", lazy="selectin")

class SubmissionRecord(Base):
    __tablename__ = "submissions"

    submission_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.student_id"), nullable=False)
    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.question_id"), nullable=False)
    timestamp = Column(String, nullable=False)
    is_correct = Column(Boolean, nullable=True)
    hint_used = Column(Boolean, nullable=True)
    submitted_code = Column(String, nullable=True)
    error_type = Column(String, nullable=True)
    failed_test_cases = Column(JSONB, nullable=True)
    ai_feedback = Column(String, nullable=True)
    streak_at_submission = Column(Integer, nullable=False, default=0)