"""
API routes — FastAPI endpoints for the sequencing system.

Endpoints:
  POST /next-question  — get the next question for a student
  POST /submit-answer   — submit the student's answer
  
Stateless endpoints support both body-based and header-based (X-Student-State) state passing.
"""

from __future__ import annotations

import logging
from uuid import UUID

from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from api_architecture.database.db import get_db
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from api_architecture.models.student_state import StudentState

from api_architecture.engine.sequencing_engine import QuestionBankExhaustedError
from api_architecture.services import question_service
from api_architecture.services.question_service import (
    ConceptLockedError,
    InvalidConceptResetError,
    InvalidSubmissionError,
    StudentNotFoundError,
)
from api_architecture.utils.stateless import (
    decode_student_state_from_header,
    StateEncodingError,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _parse_student_state_from_header(x_student_state: Optional[str]) -> Optional[StudentState]:
    """
    Parse StudentState from X-Student-State header.
    
    The header value should be base64-encoded JSON representing a StudentState.
    
    Args:
        x_student_state: The raw header value (base64-encoded JSON)
        
    Returns:
        Parsed StudentState or None if header is None/empty
        
    Raises:
        HTTPException: If the header cannot be decoded or parsed
    """
    if not x_student_state:
        return None
    
    try:
        return decode_student_state_from_header(x_student_state)
    except StateEncodingError as e:
        logger.warning("Failed to parse X-Student-State header: %s", e)
        raise HTTPException(status_code=400, detail=f"Invalid X-Student-State header: {e}")
    except Exception as e:
        logger.exception("Unexpected error parsing X-Student-State header")
        raise HTTPException(status_code=400, detail=f"Failed to parse X-Student-State header: {e}")

def _map_exception(exc: Exception, user_id) -> Optional[JSONResponse]:
    """Map service-layer exceptions to HTTP responses or raise HTTPException."""
    if isinstance(exc, HTTPException):
        raise exc
    if isinstance(exc, StudentNotFoundError):
        raise HTTPException(status_code=404, detail="Student not found")
    if isinstance(exc, ConceptLockedError):
        raise HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, (InvalidSubmissionError, InvalidConceptResetError)):
        raise HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, QuestionBankExhaustedError):
        return JSONResponse(status_code=204, content=None)
    logger.exception("Unhandled error in route for user %s", user_id)
    raise HTTPException(status_code=500, detail="Internal server error")


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class NextQuestionRequest(BaseModel):
    """POST /next-question request body."""
    user_id: UUID


class SubmitAnswerRequest(BaseModel):
    """POST /submit-answer request body."""
    user_id: UUID
    question_id: UUID
    is_correct: bool
    hint_used: bool


class ResetConceptRequest(BaseModel):
    """POST /reset-concept request body."""

    user_id: UUID
    concept_id: str


# ---------------------------------------------------------------------------
# POST /next-question
# ---------------------------------------------------------------------------


@router.post("/next-question")
async def next_question(body: NextQuestionRequest, db: AsyncSession = Depends(get_db)):
    """Return the next question for the given student.
    
    ⚠️ IMPORTANT: Call this ONLY after checking mastery
    
    Before calling this endpoint:
    - First call /submit-answer with the student's answer
    - Check the response for "concept_mastered" flag
    - If concept_mastered=true, DO NOT call this endpoint yet
      (handle concept progression first)
    - If concept_mastered=false, call this endpoint to get a new question

    Responses:
      - 200 OK: next question returned in same concept
      - 204 No Content: no questions available (question bank exhausted)
      - 403 Forbidden: concept is locked for this student
    """
    result = None
    try:
        result = await question_service.get_next_question(db, body.user_id)
    except Exception as exc:
        mapped = _map_exception(exc, body.user_id)
        if isinstance(mapped, JSONResponse):
            return mapped

    return result

# ---------------------------------------------------------------------------
# Stateless endpoints — caller supplies the full StudentState (no persistence)
#
# Supports two modes:
#   1. Body-based: Include student_state in the request body
#   2. Header-based: Send base64-encoded JSON in X-Student-State header
# ---------------------------------------------------------------------------

class NextQuestionStatelessRequest(BaseModel):
    user_id: UUID
    student_state: StudentState | None = None

class SubmitAnswerStatelessRequest(BaseModel):
    user_id: UUID
    question_id: UUID
    is_correct: bool
    hint_used: bool
    student_state: StudentState | None = None


def _resolve_student_state(
    body_state: StudentState | None,
    header_state: StudentState | None,
    user_id: UUID
) -> StudentState:
    """
    Resolve StudentState from body or header, with validation.
    
    Priority:
      1. Body-based state (if provided)
      2. Header-based state (if provided)
      
    Raises HTTPException if neither is provided.
    """
    if body_state is not None:
        logger.debug("Using body-based StudentState for user %s", user_id)
        return body_state
    
    if header_state is not None:
        logger.debug("Using header-based StudentState for user %s", user_id)
        return header_state
    
    raise HTTPException(
        status_code=400,
        detail="student_state is required. Provide it in the request body or via X-Student-State header (base64-encoded JSON)"
    )


@router.post("/next-question/stateless")
async def next_question_stateless(
    body: NextQuestionStatelessRequest,
    x_student_state: Optional[str] = Header(None, alias="X-Student-State"),
    db: AsyncSession = Depends(get_db)
):
    """
    Stateless variant: caller provides the StudentState; server processes and returns updated state.
    
    The StudentState can be provided either:
      - In the request body: {"user_id": "...", "student_state": {...}}
      - Via X-Student-State header: base64-encoded JSON of the StudentState
    
    Returns:
        {
            "updated_state": {...},  # Full updated StudentState
            "question_id": "...",
            "concept": "...",
            ...
        }
    """
    result = None
    updated_state = None
    try:
        # Parse state from header if provided
        header_state = _parse_student_state_from_header(x_student_state)
        
        # Resolve final state (body takes priority over header)
        state = _resolve_student_state(body.student_state, header_state, body.user_id)
        
        result, updated_state = await question_service.process_state_next_question(db, state)
    except Exception as exc:
        mapped = _map_exception(exc, body.user_id)
        if isinstance(mapped, JSONResponse):
            return mapped

    return {"updated_state": updated_state.model_dump(), **result}


@router.post("/submit-answer/stateless")
async def submit_answer_stateless(
    body: SubmitAnswerStatelessRequest,
    x_student_state: Optional[str] = Header(None, alias="X-Student-State"),
    db: AsyncSession = Depends(get_db)
):
    """
    Stateless variant: process a submission against provided StudentState and return updated state.
    
    The StudentState can be provided either:
      - In the request body: {"user_id": "...", "student_state": {...}, ...}
      - Via X-Student-State header: base64-encoded JSON of the StudentState
    
    Returns:
        {
            "updated_state": {...},  # Full updated StudentState
            "concept_mastered": true/false,
            "current_streak": ...,
            ...
        }
    """
    result = None
    updated_state = None
    try:
        # Parse state from header if provided
        header_state = _parse_student_state_from_header(x_student_state)
        
        # Resolve final state (body takes priority over header)
        state = _resolve_student_state(body.student_state, header_state, body.user_id)
        
        result, updated_state = await question_service.process_state_submit_answer(
            db, state, body.question_id, body.is_correct, body.hint_used
        )
    except Exception as exc:
        mapped = _map_exception(exc, body.user_id)
        if isinstance(mapped, JSONResponse):
            return mapped

    return {"updated_state": updated_state.model_dump(), **result}


# ---------------------------------------------------------------------------
# POST /submit-answer
# ---------------------------------------------------------------------------


@router.post("/submit-answer")
async def submit_answer(body: SubmitAnswerRequest, db: AsyncSession = Depends(get_db)):
    """Process a student's answer submission.

    ⚠️ IMPORTANT: Client Responsibility
    
    This endpoint returns answers submission results. The response includes a
    "concept_mastered" flag that MUST be checked by the client:
    
    - If concept_mastered=true:
      → Student has achieved mastery in the current concept
      → Client should handle progression (load next concept)
      → DO NOT call /next-question yet
      
    - If concept_mastered=false:
      → Student is still working on current concept
      → Client can call /next-question to get next question in same concept

    Example response:
    {
        "concept_mastered": false,
        "current_streak": 2,
        "attempts": 3,
        "last_answer_correct": true,
        "last_hint_used": false,
        "updated_state": {...}
    }
    
    Args:
        body: SubmitAnswerRequest with user_id, question_id, is_correct, hint_used

    Responses:
      - 200 OK: submission processed, returns streak/mastery/state data
      - 404 Not Found: student not found
      - 400 Bad Request: invalid submission (question mismatch, wrong state, etc.)
    """
    result = None
    try:
        result = await question_service.submit_answer(
        db,
            body.user_id,
            body.question_id,
            body.is_correct,
            body.hint_used,
        )
    except Exception as exc:
        mapped = _map_exception(exc, body.user_id)
        if isinstance(mapped, JSONResponse):
            return mapped

    return result


@router.post("/reset-concept")
async def reset_concept(body: ResetConceptRequest, db: AsyncSession = Depends(get_db)):
    """Reset a mastered concept so the student must re-master it."""
    result = None
    try:
        result = await question_service.reset_concept(db, body.user_id, body.concept_id)
    except Exception as exc:
        mapped = _map_exception(exc, body.user_id)
        if isinstance(mapped, JSONResponse):
            return mapped

    return result
