"""
Submission Processor — handles student answer submissions.

Updates streak, forced-resolve flag, and detects mastery after each
answer, exactly following the PROCESS_SUBMISSION specification.
"""

from __future__ import annotations

import logging
from typing import Optional

from api_architecture.models.student_state import StudentState
from api_architecture.utils.constants import MASTERY_STREAK, MIN_ATTEMPTS, CONCEPT_PROGRESSION

logger = logging.getLogger(__name__)


class SubmissionResult:
    """Thin wrapper around a student's submission data."""

    __slots__ = ("is_correct", "hint_used")

    def __init__(self, is_correct: bool, hint_used: bool) -> None:
        self.is_correct = is_correct
        self.hint_used = hint_used


def process_submission(
    state: StudentState,
    result: SubmissionResult,
) -> Optional[str]:
    """Process a student's answer and mutate *state* in-place.

    Returns
    -------
    "CONCEPT_MASTERED" if mastery is achieved after this submission,
    otherwise ``None``.
    """
    _update_forced_resolve(state, result)
    _update_streak(state, result)

    # --- Record last answer metadata --------------------------------------
    state.last_answer_correct = result.is_correct
    state.last_hint_used = result.hint_used

    # --- Post-submission mastery check ------------------------------------
    if state.attempts_in_concept >= MIN_ATTEMPTS and state.current_streak >= MASTERY_STREAK:
        _do_mastery(state)
        return "CONCEPT_MASTERED"

    return None


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _update_forced_resolve(state: StudentState, result: SubmissionResult) -> None:
    """Set the forced_resolve_active flag according to mode and submission."""
    if state.in_random_mode:
        state.forced_resolve_active = False
        return

    activate = (not result.is_correct) or result.hint_used
    state.forced_resolve_active = activate
    if activate:
        logger.info(
            "Forced resolve activated for student %s (concept %s)",
            state.student_id,
            state.current_concept,
        )
    else:
        logger.debug(
            "Forced resolve deactivated for student %s (concept %s)",
            state.student_id,
            state.current_concept,
        )

def _update_streak(state: StudentState, result: SubmissionResult) -> None:
    """Update the student's streak following the submission rules."""
    # Streak increments ONLY for correct + no hint + first-presentation
    if not result.is_correct:
        state.current_streak = 0
        logger.debug("Streak reset to 0 for student %s", state.student_id)
        return

    if result.hint_used:
        state.current_streak = 0
        logger.debug("Streak reset to 0 for student %s", state.student_id)
        return

    if state.last_question_was_new:
        state.current_streak += 1
        logger.debug(
            "Streak incremented to %d for student %s",
            state.current_streak,
            state.student_id,
        )
        return

    # else: correct + no hint but NOT new → streak unchanged

def _do_mastery(state: StudentState) -> None:
    """Update state for concept mastery and unlock next concept."""
    concept = state.current_concept
    if concept not in state.mastered_concepts:
        state.mastered_concepts = state.mastered_concepts + [concept]
    logger.info("Student %s mastered concept %s", state.student_id, concept)

    idx = CONCEPT_PROGRESSION.index(concept) if concept in CONCEPT_PROGRESSION else -1
    if idx >= 0 and idx + 1 < len(CONCEPT_PROGRESSION):
        next_concept = CONCEPT_PROGRESSION[idx + 1]
        if next_concept not in state.unlocked_concepts:
            state.unlocked_concepts = state.unlocked_concepts + [next_concept]
            logger.info(
                "Concept %s unlocked for student %s",
                next_concept,
                state.student_id,
            )
        # Advance to next concept & reset
        state.current_concept = next_concept

    state.attempts_in_concept = 0
    state.current_streak = 0
    state.current_error_type_index = 0
    state.in_random_mode = False
    state.forced_resolve_active = False
    state.last_question_was_new = False
    state.recent_question_ids = []
    state.presented_question_ids = []
