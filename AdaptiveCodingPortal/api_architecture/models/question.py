"""
Pydantic models for Question data.

Represents a question record from the questions table.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class Question(BaseModel):
    """A single question from the question bank."""

    model_config = ConfigDict(from_attributes=True)

    question_id: UUID
    concept: str
    error_type: str

    question: str = ""
    solution: Optional[str] = None
    test_cases: Optional[Any] = None
    language: str = "python"
    metadata: Optional[Dict[str, Any]] = None
