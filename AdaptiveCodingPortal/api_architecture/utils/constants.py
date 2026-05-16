"""
Constants and configuration for the Question Sequencing Algorithm.

Contains priority orders, thresholds, and concept progression chain
as defined in the algorithm specification.
"""

from typing import List

# ---------------------------------------------------------------------------
# Error-type priority order (concept-aware)
# ---------------------------------------------------------------------------

BASE_PRIORITY_ORDER: List[str] = [
    "Syntax",
    "Conceptual",
    "Input",
    "Variable",
    "ArrayString",
    "Condition",
    "Loop",
    "Computation",
    "Branching",
    "Output",
]


def get_priority_order(concept_id: str) -> List[str]:
    """Return the error-type priority order for a given concept.

    For concept C6 (Functions), the 'Function' error type is inserted
    after 'Conceptual'.
    """
    if concept_id == "C6":
        return BASE_PRIORITY_ORDER[:2] + ["Function"] + BASE_PRIORITY_ORDER[2:]
    return list(BASE_PRIORITY_ORDER)


# ---------------------------------------------------------------------------
# Mastery / attempt thresholds
# ---------------------------------------------------------------------------

MIN_ATTEMPTS: int = 8
"""Hard floor — minimum unique-question attempts before mastery check."""

MASTERY_STREAK: int = 4
"""Consecutive correct (no-hint, first-presentation) answers needed to master."""

RECENT_QUESTIONS_MAX: int = 5
"""Maximum number of recent question IDs to track for exclusion."""

# ---------------------------------------------------------------------------
# Concept progression chain (ordered list of concept identifiers)
# ---------------------------------------------------------------------------

CONCEPT_PROGRESSION: List[str] = [
    "C1",  # Conditionals [If-else]
    "C2",  # Basic Loops [For / While]
    "C3",  # Loops with Lists
    "C4",  # Nested Loops
    "C5",  # Strings
    "C6",  # Functions
]
