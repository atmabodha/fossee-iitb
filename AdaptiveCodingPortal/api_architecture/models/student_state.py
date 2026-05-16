"""
Pydantic models for Student State.

Mirrors the StudentState dataclass from the algorithm specification
with full type annotations.
"""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import declarative_base


class StudentState(BaseModel):
    """Persistent state tracked per student for the sequencing algorithm."""

    model_config = ConfigDict(from_attributes=True)

    student_id: UUID
    current_concept: str = "C1"
    attempts_in_concept: int = 0
    current_streak: int = 0
    current_error_type_index: int = 0

    last_question_id: Optional[UUID] = None
    last_error_type: Optional[str] = None
    last_answer_correct: Optional[bool] = None
    last_hint_used: Optional[bool] = None

    in_random_mode: bool = False
    forced_resolve_active: bool = False
    last_question_was_new: bool = False

    recent_question_ids: List[str] = Field(default_factory=list)
    presented_question_ids: List[str] = Field(default_factory=list)

    attempted_concepts: List[str] = Field(default_factory=list)
    mastered_concepts: List[str] = Field(default_factory=list)
    unlocked_concepts: List[str] = Field(default_factory=lambda: ["C1"])

    state_version: int = 0
