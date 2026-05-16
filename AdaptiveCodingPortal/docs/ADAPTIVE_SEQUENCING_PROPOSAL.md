# Project Proposal: Adaptive Question Sequencing Module for Yaksh

---

## 1. Introduction

The Yaksh platform currently employs a static, predetermined sequence for question delivery, which does not accommodate individual learning needs or ensure mastery of concepts. This limitation restricts the platform’s effectiveness in reinforcing weak areas and promoting comprehensive understanding.

This proposal outlines the integration of an adaptive question sequencing module into Yaksh. The proposed system dynamically selects questions based on each student’s performance, thereby facilitating structured learning, targeted remediation, and mastery-based progression.

---

## 2. Problem Statement

- The existing system does not adapt to student performance.
- Students may progress without addressing conceptual weaknesses.
- There is no mechanism to enforce mastery before advancing to subsequent concepts.
- Error types are not systematically targeted, reducing the efficacy of remediation.

---

## 3. Proposed Solution

A dedicated Django application will be developed and integrated as a separate module within Yaksh. This module will:

- Persistently track each student’s progress and mastery status.
- Dynamically select questions according to error types and performance metrics.
- Enforce strict mastery requirements prior to progression.
- Store all progression and interaction data in a PostgreSQL database to ensure data integrity and facilitate analytics.

---

## 4. Database Design (PostgreSQL Schema)

**Principle:**  
While the sequencing logic remains stateless and deterministic, the Django application will persist student progression and interaction metadata.

### 4.1 StudentState Table

| Field                   | Type         | Description                                   |
|-------------------------|--------------|-----------------------------------------------|
| student_id              | UUID (FK)    | References user                               |
| current_concept         | String       | Current concept in progression                |
| current_error_type_index| Integer      | Index for error-type cycling                  |
| attempts_in_concept     | Integer      | Attempts made in current concept              |
| current_streak          | Integer      | Current streak of correct answers             |
| forced_resolve_active   | Boolean      | Forced resolve mode active                    |
| in_random_mode          | Boolean      | Random mode active                            |
| last_question_id        | UUID (FK)    | Last question served                          |
| last_question_was_new   | Boolean      | Indicates if last question was new            |
| state_version           | Integer      | Schema version                                |

### 4.2 StudentProgress Table

| Field               | Type           | Description                        |
|---------------------|----------------|------------------------------------|
| student_id          | UUID (FK)      | References user                    |
| attempted_concepts  | Array[String]  | Concepts attempted                 |
| mastered_concepts   | Array[String]  | Concepts mastered                  |
| unlocked_concepts   | Array[String]  | Concepts unlocked                  |

### 4.3 Question Table

| Field           | Type         | Description                        |
|-----------------|--------------|------------------------------------|
| question_id     | UUID (PK)    | Unique question identifier         |
| concept         | String       | Associated concept                 |
| error_type      | String       | Error category                     |
| difficulty      | String       | Difficulty label                   |
| content         | Text         | Question prompt/content            |
| solution        | Text         | Solution (optional)                |

### 4.4 Submission Table (Recommended)

| Field           | Type         | Description                        |
|-----------------|--------------|------------------------------------|
| submission_id   | UUID (PK)    | Unique submission identifier       |
| student_id      | UUID (FK)    | References user                    |
| question_id     | UUID (FK)    | References question                |
| is_correct      | Boolean      | Indicates correctness              |
| hint_used       | Boolean      | Indicates if hint was used         |
| timestamp       | Timestamp    | Submission time                    |

**Note:**  
The database is designed to store only student progression and interaction metadata. The sequencing logic itself remains stateless and deterministic.

### 4.5 Database Relationships and Constraints

**Foreign Key Relationships:**
- `StudentState.student_id` → `auth_user.id` (Django built-in)
- `StudentState.last_question_id` → `Question.question_id`
- `StudentProgress.student_id` → `auth_user.id`
- `Submission.student_id` → `auth_user.id`
- `Submission.question_id` → `Question.question_id`

**Key Constraints:**
- `StudentState`: Primary key is `student_id` (one state per student per course module)
- `StudentProgress`: Primary key is `student_id` (one progress record per student per module)
- `Question`: Unique constraint on `(concept, error_type, difficulty)` to prevent duplicate questions
- `Submission`: Records all submissions for audit trail and analytics

**Cascade Behaviors:**
- When a user is deleted, cascade delete all related `StudentState`, `StudentProgress`, and `Submission` records
- When a `Question` is deleted, cascade delete related `Submission` records but preserve state (state references question_id but can handle missing questions gracefully)

### 4.6 Django Model Examples (Pseudocode)

The following are simplified pseudocode representations of the Django ORM models (not production code):

```python
from django.db import models
from django.contrib.auth.models import User
import uuid

class Question(models.Model):
    question_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    concept = models.CharField(max_length=100, db_index=True)
    error_type = models.CharField(max_length=50, db_index=True)
    difficulty = models.CharField(max_length=20, choices=[
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard')
    ])
    content = models.TextField()
    solution = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('concept', 'error_type', 'difficulty')
        indexes = [
            models.Index(fields=['concept', 'error_type']),
        ]

class StudentState(models.Model):
    student = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    current_concept = models.CharField(max_length=100, db_index=True)
    current_error_type_index = models.IntegerField(default=0)
    attempts_in_concept = models.IntegerField(default=0)
    current_streak = models.IntegerField(default=0)
    forced_resolve_active = models.BooleanField(default=False)
    in_random_mode = models.BooleanField(default=False)
    last_question = models.ForeignKey(
        Question, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    last_question_was_new = models.BooleanField(default=True)
    state_version = models.IntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['student', 'current_concept']),
        ]

class StudentProgress(models.Model):
    student = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    attempted_concepts = models.JSONField(default=list)
    mastered_concepts = models.JSONField(default=list)
    unlocked_concepts = models.JSONField(default=list)
    updated_at = models.DateTimeField(auto_now=True)

class Submission(models.Model):
    submission_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.SET_NULL, null=True)
    is_correct = models.BooleanField()
    hint_used = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['student', 'timestamp']),
            models.Index(fields=['question', 'is_correct']),
        ]
```

### 4.7 Indexing Strategy for Performance

**Critical Indexes (Must Have):**
1. `StudentState(student_id, current_concept)` — Fast retrieval of student state by student and concept for state transitions
2. `Question(concept, error_type)` — Fast filtering of available questions by concept and error type during sequencing
3. `Submission(student_id, timestamp)` — Fast retrieval of recent submissions for analytics and auditing

**Secondary Indexes (Recommended):**
4. `Question(difficulty)` — For future difficulty-based filtering if needed
5. `StudentProgress(student_id)` — Inherent due to primary key; supports cascade operations efficiently
6. `Submission(question_id, is_correct)` — For question performance analytics

**Index Maintenance:**
- Review indexes after 6 months of production data
- Add composite indexes if slow queries detected (use `django-extensions` or PostgreSQL's EXPLAIN ANALYZE)
- Consider partial indexes if "in_random_mode = TRUE" questions differ significantly in access patterns

### 4.8 State Version Field Explanation

The `state_version` field in `StudentState` tracks the schema version of the state object. This enables:
- **Backward Compatibility:** If the state schema is updated (e.g., adding a new field), old records can be identified and migrated safely
- **Zero-Downtime Deployments:** Allows new code to handle both old and new state versions during rollout
- **Audit Trail:** Records which version of the algorithm was used for each state

**Example Migration Strategy:**
```
if state_version == 1:
    # Old schema: missing 'random_seed' field
    state.random_seed = generate_random_seed()
    state.state_version = 2
    state.save()
```

---

## 5. Algorithm Overview (Reflecting Actual Implementation)

**Core Principles and Behaviors:**

1. **Linear Concept Progression:**  
   - Concepts must be completed sequentially; skipping is not permitted.
   - Only unlocked concepts can be attempted; progression is strictly enforced.

2. **Error-Type Cycling and Adaptive Learning:**  
   - Each concept is subdivided into error types (e.g., Syntax, Logic).
   - The system cycles through error types in a deterministic order.
   - After each correct answer (without hint), the error type advances; incorrect answers or hint usage activate forced resolve, causing the same question to be repeated until resolved.

3. **Streak and Attempt Counting:**  
   - Streak increments only for correct answers on new questions without hints.
   - Streak resets to zero on any incorrect answer or if a hint is used.
   - Forced resolve mode is activated on incorrect answers or hint usage; in this mode, repeated questions do not increment attempts or streak.
   - Attempts are incremented only for new questions (not for forced resolve retries).

4. **Mastery Rule:**  
   - A concept is considered mastered only if:  
     $$
     \text{Attempts} \geq 8 \quad \text{AND} \quad \text{Streak} \geq 4
     $$
   - Upon mastery, the current concept is marked as mastered, the next concept is unlocked, and the state is reset for the new concept.

5. **Random Mode Activation:**  
   - If a student reaches 8 or more attempts in a concept without achieving a streak of 4, random mode is activated.
   - In random mode, error types are selected randomly (excluding the last error type served), and forced resolve is deactivated.
   - Random mode continues until mastery is achieved.

6. **Edge Cases and Consistency:**  
   - Mastery is not triggered unless both attempt and streak thresholds are met.
   - State transitions are validated to prevent progression to locked concepts.
   - All state mutations are deterministic and reproducible.

**Summary:**  
The sequencing engine operates as a deterministic state machine, precisely tracking student progress, enforcing mastery, and adapting question selection based on correctness, streaks, attempt counts, and error-type coverage. Forced resolve and random mode ensure that students address weaknesses and cannot bypass conceptual gaps.

### 5.1 State Machine Description

**State Transition Flow:**

The system manages student progression through clearly defined state transitions:

```
┌─────────────────────────────────────────────────────────────────┐
│                    NORMAL MODE (Initial)                        │
│  Serve next question based on error_type_index                  │
│  Increment attempts on new questions only                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    ┌─────────┴─────────┐
                    │                   │
         [Correct]  │               [Incorrect or Hint]
                    │                   │
                    ↓                   ↓
          ┌──────────────────┐  ┌──────────────────────┐
          │ Increment Streak │  │ FORCED RESOLVE MODE  │
          │ Advance Error-   │  │ Repeat last question │
          │ Type Index       │  │ Don't count attempts │
          └──────────────────┘  │ Reset streak to 0    │
                    │           └──────────────────────┘
                    │                   ↓
            ┌───────┴─────────┬─────────────────┐
            │                 │                 │
      [Attempts ≥ 8]    [Specific Conditions]   │
      [AND Streak ≥ 4]     (See below)          │
            │                 │                 │
            ↓                 ↓                 ↓
      ┌──────────────┐   ┌──────────────────┐   │
      │  MASTERY ✓   │   │ Check for       │   │
      │  Unlock next │   │ Fixed Resolve   │   │
      │  concept     │   └──────────────────┘   │
      │  Reset state │           ↓              │
      └──────────────┘   [Correct in Forced    │
            │            Resolve?]             │
            │                 │                │
            │             [Yes]│   [No]       │
            │              └───┴──────┴────┘
            │                   │
            │           ┌───────┴────────┐
            │           │                │
            │     [Attempts ≥ 8]    [Try again]
            │     [Streak < 4]      [Stay in FP]
            │           │
            │           ↓
            │    ┌──────────────────┐
            │    │ RANDOM MODE      │
            │    │ Select error-    │
            │    │ type randomly    │
            │    │ Deactivate FP    │
            │    └──────────────────┘
            │           ↓
            │    ┌───────────────────┐
            │    │ Continue until    │
            │    │ Streak ≥ 4 AND   │
            │    │ Attempts ≥ 8      │
            │    └───────────────────┘
            │           ↓
            └───────────────────────────
                        ↓
              ┌──────────────────┐
              │  Next Concept    │
              │  Start New State │
              └──────────────────┘
```

**State Transition Triggers:**

1. **Normal → Forced Resolve:** When submission has `is_correct = False` OR `hint_used = True`
2. **Forced Resolve → Normal:** When submission in forced resolve mode has `is_correct = True`
3. **Normal → Random Mode:** When `attempts_in_concept >= 8` AND `current_streak < 4` AND not already in random mode
4. **Any Mode → Mastery:** When `attempts_in_concept >= 8` AND `current_streak >= 4`
5. **Mastery → Next Concept:** Automatically triggered; resets state for new concept, unlocks next concept

### 5.2 Worked Example: One Student's Journey (Simplified)

**Scenario:** Student "Alice" is learning the "Variables" concept with three error types: `[Syntax, Logic, Type]`.

**Initial State:**
```
student_id: alice123
current_concept: Variables
current_error_type_index: 0  (pointing to Syntax)
attempts_in_concept: 0
current_streak: 0
forced_resolve_active: False
in_random_mode: False
```

**Attempt 1 - Question: "Q1: Syntax error in variable declaration"**
```
[Backend selects Question with concept=Variables, error_type=Syntax]
→ Backend returns Q1 to frontend
→ Student submits answer: WRONG
```
**State After Attempt 1 (FORCED RESOLVE ACTIVATED):**
```
attempts_in_concept: 1  ← incremented (NEW question)
current_streak: 0        ← reset due to wrong answer
forced_resolve_active: True
last_question_id: Q1
last_question_was_new: True
```

**Attempt 2 - Question: SAME Q1 (forced resolve mode)**
```
[Backend detects forced_resolve_active = True]
→ Returns SAME Q1 again
→ Student submits answer: CORRECT
```
**State After Attempt 2 (FORCED RESOLVE DEACTIVATED):**
```
attempts_in_concept: 1   ← NOT incremented (repeat, not new)
current_streak: 1        ← incremented (correct answer)
forced_resolve_active: False
current_error_type_index: 1  ← advanced to Logic
last_question_was_new: False
```

**Attempt 3 - Question: "Q2: Logic error in variable scope"**
```
[Backend selects Question with concept=Variables, error_type=Logic]
→ Returns Q2 to frontend
→ Student submits answer: CORRECT
```
**State After Attempt 3:**
```
attempts_in_concept: 2   ← incremented (new question)
current_streak: 2        ← incremented
current_error_type_index: 2  ← advanced to Type
last_question_id: Q2
last_question_was_new: True
```

**Attempts 4-9:** Alice continues, gets Q3 (Type error) wrong at attempt 4, enters forced resolve, recovers, then gets Q1 (cycles back to Syntax) wrong at attempt 5.

```
After Attempt 9 (hypothetical state):
attempts_in_concept: 8
current_streak: 4
→ MASTERY ACHIEVED ✓
```

**State After Mastery:**
```
student_id: alice123
current_concept: Functions        ← SWITCHED to next concept
attempts_in_concept: 0            ← RESET
current_streak: 0                 ← RESET
current_error_type_index: 0       ← RESET to first error type
forced_resolve_active: False      ← RESET
in_random_mode: False             ← RESET
forced_resolve_active: False
```

**StudentProgress is Updated:**
```
mastered_concepts: ["Variables"]
unlocked_concepts: ["Variables", "Functions", "Conditionals"]  ← Functions now available
attempted_concepts: ["Variables", "Functions"]
```

Alice has now mastered "Variables" and can proceed to "Functions."

### 5.3 Error-Type Cycling Mechanics

**Deterministic Ordering:**

Each concept (e.g., "Variables") is subdivided into a predefined, ordered list of error types:
```python
error_type_order = {
    "Variables": ["Syntax", "Logic", "Type"],
    "Functions": ["Definition", "Calling", "Return"],
    "Loops": ["Syntax", "Termination", "Logic"],
}
```

**Index Cycling:**

- The `current_error_type_index` is an integer pointing to the current position in the ordered list
- **Example:** For "Variables" concept:
  - Index 0 → "Syntax" error type
  - Index 1 → "Logic" error type
  - Index 2 → "Type" error type
  - Index wraps: Index 3 would cycle back to Index 0 ("Syntax")

**Advancement Logic (Normal Mode):**
```
IF submission.is_correct AND NOT submission.hint_used:
    current_error_type_index = (current_error_type_index + 1) % len(error_types)
    streak += 1
ELSE:
    forced_resolve_active = True
    streak = 0
```

**Random Mode (When Attempts ≥ 8 and Streak < 4):**
```
IF in_random_mode:
    available_error_types = error_type_order[current_concept] 
                            - {last_error_type_served}  # exclude last
    selected_error_type = random.choice(available_error_types)
    # Query: Question(concept=current_concept, error_type=selected_error_type)
```

**Why Cycling Through Error Types?**
- **Comprehensive Coverage:** Ensures students face different types of errors within a concept
- **Prevents One-Trick Ponies:** A student can't just memorize one error-type's solutions
- **Targeted Remediation:** Moving through error types systematically addresses root causes of misunderstanding

### 5.4 Extended Edge Cases and Resolution

**Case 1: Student Submits While in Forced Resolve with No Last Question**
- **Problem:** Last question ID is NULL unexpectedly
- **Resolution:** Treat as unlock failure; serve first question of current concept; log as potential data corruption
- **Prevention:** Always set `last_question_id` before handing question to frontend

**Case 2: Concept Progression During Mid-Concept Forced Resolve**
- **Problem:** Student masters concept while in forced resolve mode (edge case)
- **Resolution:** Locked; mastery requires streak ≥ 4, and forced resolve resets streak to 0, so mastery cannot occur in forced resolve
- **Prevention:** Validation logic in mastery check prevents this

**Case 3: Simultaneous Submissions (Race Condition)**
- **Problem:** Two submissions arrive before state is updated
- **Resolution:** Use database-level locking or atomic transactions; second update overwrites first (LOST UPDATE problem)
- **Prevention:** Implement optimistic locking with version field in `StudentState`

**Case 4: Random Mode Question Not Found**
- **Problem:** No questions exist for (concept, error_type) pair in random mode
- **Resolution:** Fall back to deterministic cycling; deactivate random mode; log warning
- **Prevention:** Validate that all error types have at least 2 questions per concept during course setup

**Case 5: Attempts/Streak Mismatch After System Crash**
- **Problem:** State data becomes inconsistent (e.g., attempts = 5, streak = 9, which is impossible)
- **Resolution:** Use `state_version` field to identify and migrate inconsistent states; reconstruct from `Submission` table audit trail if needed
- **Prevention:** Idempotent state updates; store before/after snapshots in `Submission` records

---

## 6. System Architecture

**Overview:**

- **Frontend (Yaksh UI):** User interface for question delivery and answer submission.
- **Django Application (New Module):** Handles state management and sequencing logic.
- **Sequencing Engine (Python Logic):** Implements the adaptive algorithm.
- **PostgreSQL Database:** Stores student state and progression data.

## 7. API Workflow

### 7.1 Endpoint: POST /next-question

**Purpose:** Retrieve the next question for a student based on their current state and sequencing algorithm.

**Request Schema:**
```json
{
  "student_id": "string (UUID)",
  "concept_id": "string (optional)"
}
```

**Request Field Descriptions:**
- `student_id` (required, UUID): Unique identifier of the student in Yaksh system
- `concept_id` (optional, string): If specified, override and fetch question for this concept (useful for testing or remediation)

**Response Schema (Success - 200):**
```json
{
  "success": true,
  "question": {
    "question_id": "uuid",
    "concept": "Variables",
    "error_type": "Syntax",
    "content": "Write a variable declaration for...",
    "difficulty": "medium"
  },
  "student_state": {
    "student_id": "uuid",
    "current_concept": "Variables",
    "attempts_in_concept": 2,
    "current_streak": 1,
    "forced_resolve_active": false,
    "in_random_mode": false
  }
}
```

**Response Field Descriptions:**
- `success`: Boolean indicating request success
- `question`: The question object to display to student
- `student_state`: Current state snapshot (for frontend display of progress)

**Error Responses:**
- `404 Not Found`: Student ID does not exist
- `400 Bad Request`: Missing required `student_id` field or invalid UUID format
- `409 Conflict`: Student has not unlocked the requested concept (if `concept_id` provided)
- `500 Internal Server Error`: Database error or algorithm failure

### 7.2 Endpoint: POST /submit-answer

**Purpose:** Record student's answer submission and update state; return next question and mastery status.

**Request Schema:**
```json
{
  "student_id": "string (UUID)",
  "question_id": "string (UUID)",
  "is_correct": "boolean",
  "hint_used": "boolean"
}
```

**Request Field Descriptions:**
- `student_id` (required, UUID): Student identifier
- `question_id` (required, UUID): ID of the question being answered
- `is_correct` (required, boolean): Whether the student's answer was correct
- `hint_used` (required, boolean): Whether the student used a hint before submitting

**Response Schema (Success - 200):**
```json
{
  "success": true,
  "submission_id": "uuid",
  "updated_state": {
    "student_id": "uuid",
    "current_concept": "Variables",
    "attempts_in_concept": 3,
    "current_streak": 2,
    "forced_resolve_active": false,
    "in_random_mode": false,
    "mastery_achieved": false
  },
  "feedback": {
    "is_correct": true,
    "streak_count": 2,
    "attempts_count": 3,
    "message": "Great! You've got 2 in a row. Keep going!"
  },
  "next_question": {
    "question_id": "uuid",
    "concept": "Variables",
    "error_type": "Logic",
    "content": "What will this code output..."
  },
  "mastery_event": null
}
```

**Special Response When Mastery is Achieved:**
```json
{
  "success": true,
  "submission_id": "uuid",
  "updated_state": {
    "current_concept": "Variables",
    "attempts_in_concept": 8,
    "current_streak": 4,
    "mastery_achieved": true
  },
  "feedback": {
    "is_correct": true,
    "message": "Congratulations! You've mastered Variables!"
  },
  "mastery_event": {
    "previous_concept": "Variables",
    "mastered_concepts": ["Variables"],
    "next_concept": "Functions",
    "unlocked_concepts": ["Variables", "Functions", "Conditionals"]
  },
  "next_question": {
    "question_id": "uuid",
    "concept": "Functions",
    "error_type": "Definition",
    "content": "Define a function that..."
  }
}
```

**Error Responses:**
- `404 Not Found`: Student or question not found
- `400 Bad Request`: Invalid request fields or missing required data
- `409 Conflict`: Question ID does not match student's last served question (state mismatch)
- `422 Unprocessable Entity`: Question not available for student's current concept (e.g., submitted answer for wrong concept)
- `500 Internal Server Error`: State update or algorithm failure

### 7.3 Backend Processing Workflow

**For POST /next-question:**

1. **Validate Input:** Verify `student_id` is valid UUID and exists in system
2. **Retrieve State:** Fetch `StudentState` record for this student from database
3. **Initialize if Needed:** If no state exists, create initial state with first concept unlocked
4. **Check Concept Lock:** If `concept_id` requested, ensure it's in `unlocked_concepts`; else use `current_concept`
5. **Determine Error Type:** Based on `current_error_type_index` and `in_random_mode`:
   - If normal mode: error_type = error_types[current_concept][index]
   - If random mode: error_type = random choice from available error types
6. **Query Question:** Fetch question matching `(concept, error_type, difficulty)` that hasn't been served recently
7. **Update State Metadata:** Set `last_question_id`, `last_question_was_new = True`
8. **Save State:** Update database with new question reference
9. **Return Response:** Send question + state snapshot to frontend

**For POST /submit-answer:**

1. **Validate Input:** Verify all required fields; validate UUIDs
2. **Fetch State:** Retrieve current `StudentState` for this student
3. **Verify Question Match:** Ensure `question_id` matches `last_question_id` in state
4. **Determine New State:** Based on `is_correct`, `hint_used`, current `forced_resolve_active`:
   - If forced resolve active:
     - If correct: exit forced resolve, advance error type, increment streak
     - If incorrect: stay in forced resolve, keep same question, reset streak
   - If normal mode:
     - If correct: increment streak, advance error type
     - If incorrect: enter forced resolve, reset streak
5. **Increment Attempts:** Only if new question (`last_question_was_new = True`)
6. **Check Mastery:** If `attempts >= 8` AND `streak >= 4`, trigger mastery:
   - Mark concept as mastered
   - Unlock next concept
   - Reset state for next concept
7. **Check Random Mode:** If `attempts >= 8` AND `streak < 4` AND not in random mode, activate random mode
8. **Record Submission:** Create `Submission` record for audit trail
9. **Save State:** Persist updated `StudentState` to database
10. **Fetch Next Question:** Execute steps 5-9 from `/next-question` workflow
11. **Build Response:** Include updated state, feedback, and next question

### 7.4 State Transition Response Example

**Before Submission (Student at 7 attempts, streak 3 in Variables):**
```json
{
  "student_id": "alice-123",
  "current_concept": "Variables",
  "attempts_in_concept": 7,
  "current_streak": 3,
  "forced_resolve_active": false,
  "in_random_mode": true
}
```

**Submission: Question = Q45 (error_type: Type), is_correct: true, hint_used: false**

**After Submission (Mastery Triggered):**
```json
{
  "success": true,
  "submission_id": "sub-789",
  "updated_state": {
    "student_id": "alice-123",
    "current_concept": "Functions",
    "attempts_in_concept": 0,
    "current_streak": 0,
    "forced_resolve_active": false,
    "in_random_mode": false,
    "mastery_achieved": true
  },
  "mastery_event": {
    "previous_concept": "Variables",
    "mastery_triggered_at": "2026-04-06T10:45:22Z",
    "mastered_concepts": ["Variables"],
    "next_concept": "Functions",
    "unlocked_concepts": ["Variables", "Functions", "Conditionals", "Data Structures"]
  },
  "feedback": {
    "is_correct": true,
    "message": "Excellent! You've mastered Variables!",
    "streak_before": 3,
    "streak_after": 1,
    "attempts_total": 8
  }
}
```

### 7.5 Query Parameters and Advanced Options

**Optional Query Parameters for /next-question:**

- `dry_run=true` (boolean): Fetch next question WITHOUT updating state; useful for testing
- `concept_override=<concept_id>` (string): Force fetch question from specific concept (admin/testing only)
- `error_type_override=<error_type>` (string): Force fetch question with specific error type (testing only)

**Example:**
```
POST /next-question?dry_run=true
{
  "student_id": "alice-123"
}
```

This will return the next question WITHOUT updating `last_question_id` or state, useful for previewing or testing workflow.

**Key Point:**  
This two-step interaction model ensures a clear separation of concerns between question retrieval and answer submission. The stateless algorithm nature means each API call independently verifies the student state against the database, ensuring consistency even if intermediate requests fail.
---

#### Endpoint 2: Submit Answer
**Request:**
```
POST /api/v1/sequencing/submit-answer
Content-Type: application/json
```

**Request Schema:**
```json
{
  "student_id": "uuid",
  "question_id": "uuid",
  "session_id": "uuid",
  "answer": {
    "value": "string | number | array",
    "response_time_seconds": integer
  },
  "hint_used": boolean,
  "hint_id": "uuid (optional)"
}
```

**Response Schema (200 OK):**
```json
{
  "status": "success",
  "data": {
    "is_correct": boolean,
    "points_earned": integer,
    "feedback": "string",
    "correct_answer": "string (if incorrect)",
    "explanation": "string",
    "state_update": {
      "current_mastery": {
        "topic": "string",
        "mastery_score": float,
        "confidence_interval": [float, float]
      },
      "topics_mastered": ["string"],
      "topics_in_progress": ["string"],
      "recommended_next_topic": "string"
    },
    "session_stats": {
      "correct_count": integer,
      "incorrect_count": integer,
      "accuracy": float,
      "average_response_time": float
    }
  },
  "timestamp": "ISO-8601"
}
```

**Error Responses:**
- `400 Bad Request` - Invalid answer format or missing required fields
- `404 Not Found` - Question or student session not found
- `409 Conflict` - Answer already submitted for this question
- `500 Internal Server Error` - State update failure

---

### 7.2 Backend Processing Workflow

**Step 1: Retrieve Next Question Flow**
```
1. Validate student_id and session_id
2. Fetch student state from PostgreSQL
3. Load prerequisite graph and mastery data
4. Execute sequencing algorithm:
   - Calculate student knowledge state
   - Evaluate mastery thresholds
   - Apply adaptive difficulty rules
   - Select optimal next question
5. Cache question context in Redis (TTL: 300s)
6. Return question with metadata
```

**Step 2: Submit Answer Processing Flow**
```
1. Validate answer submission format
2. Check for duplicate submissions (idempotency)
3. Grade answer against expected response
4. Calculate performance metrics:
   - Correctness classification
   - Response time analysis
   - Difficulty adjustment factor
5. Update Bayesian knowledge state:
   - Recalculate mastery probability
   - Update confidence bounds
   - Evaluate topic mastery criteria
6. Persist updates to PostgreSQL
7. Trigger prerequisite re-evaluation
8. Return updated state and feedback
```

---

### 7.3 State Transition Examples

**Example 1: Correct Answer - Topic Progression**
```
Initial State:
- Topic: "Algebra Basics"
- Mastery: 0.65 (65%)
- Attempts: 8
- Last Correct: 2 questions back

Answer: CORRECT
Response Time: 12 seconds

Result:
- Mastery Updated: 0.65 → 0.72 (Bayesian update)
- Status: In Progress → Ready for Next Topic
- Recommendation: "Proceed to Quadratic Equations"
- Prerequisite Unlock: "Advanced Functions" now available
```

**Example 2: Incorrect Answer - Hint Triggered**
```
Initial State:
- Topic: "Polynomial Division"
- Mastery: 0.42 (42%)
- Streak: Correct × 2
- Hints Available: 3

Answer: INCORRECT
Hint Used: YES (Hint 1)

Result:  
- Mastery Updated: 0.42 → 0.38 (slight decrease)
- Difficulty Adjusted: Current → One Level Easier
- Status: In Progress (maintained)
- Next Question: Similar difficulty with different values
- Hint Remaining: 2
```

---

### 7.4 Query Parameters and Filters

**GET /api/v1/sequencing/student/{student_id}/progress**

Query Parameters:
- `topic` (optional): Filter by specific topic (e.g., "Algebra")
- `start_date` (optional): ISO-8601 date for session filtering
- `end_date` (optional): ISO-8601 date for session filtering
- `include_history` (boolean, default: false): Include detailed attempt history
- `limit` (integer, default: 50): Pagination limit
- `offset` (integer, default: 0): Pagination offset

Example Request:
```
GET /api/v1/sequencing/student/uuid-123/progress?topic=Algebra&include_history=true&limit=100
```

**Response Schema:**
```json
{
  "student_id": "uuid",
  "progress_data": {
    "topics": [
      {
        "name": "string",
        "mastery_level": float,
        "status": "not_started | in_progress | mastered",
        "attempts": integer,
        "timestamp_last_attempt": "ISO-8601"
      }
    ],
    "overall_progress": float,
    "estimated_time_to_completion": integer
  }
}
```

---

### 7.5 Error Handling Strategy

**Validation Errors (400):**
- Missing required fields → Return field-specific error messages
- Type mismatches → Provide expected vs actual type information
- Invalid UUIDs → Reject with validation error

**State Errors (409):**
- Duplicate submissions → Return original response from cache
- Concurrent state updates → Implement optimistic locking with retry logic
- Stale session data → Prompt client to refresh session

**Server Errors (500):**
- Database connection failure → Implement circuit breaker pattern
- Algorithm execution timeout → Return fallback question from cache
- State calculation error → Log error and notify monitoring system

**Client Recovery:**
- Automatic retry with exponential backoff for 5xx errors
- Fallback questions for algorithm failures
- Graceful degradation if hints unavailable

---

**Key Point:**  
This comprehensive API design ensures reliable, efficient sequencing through well-defined endpoints, clear request/response contracts, robust error handling, and transparent state management that enables both immediate question delivery and long-term student progress tracking.

  "status": "success",
  "data": {
    "question_id": "uuid",
    "question_text": "string",
    "question_type": "multiple_choice | free_response | numerical",
    "options": ["string"],
    "difficulty_level": integer,
    "topic": "string",
    "time_limit_seconds": integer,
    "metadata": {
      "prerequisite_mastery": [{"topic": "string", "mastery_level": float}]
    }
  },
  "timestamp": "ISO-8601"
}
```

**Error Responses:**
- `400 Bad Request` - Invalid student_id or session parameters
- `404 Not Found` - Student record not found
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Backend processing error

---

#### Endpoint 2: Submit Answer
**Request:**
```
POST /api/v1/sequencing/submit-answer
Content-Type: application/json
```

**Request Schema:**
```json
{
  "student_id": "uuid",
  "question_id": "uuid",
  "session_id": "uuid",
  "answer": {
    "value": "string | number | array",
    "response_time_seconds": integer
  },
  "hint_used": boolean,
  "hint_id": "uuid (optional)"
}
```

**Response Schema (200 OK):**
```json
{
  "status": "success",
  "data": {
    "is_correct": boolean,
    "points_earned": integer,
    "feedback": "string",
    "correct_answer": "string (if incorrect)",
    "explanation": "string",
    "state_update": {
      "current_mastery": {
        "topic": "string",
        "mastery_score": float,
        "confidence_interval": [float, float]
      },
      "topics_mastered": ["string"],
      "topics_in_progress": ["string"],
      "recommended_next_topic": "string"
    },
    "session_stats": {
      "correct_count": integer,
      "incorrect_count": integer,
      "accuracy": float,
      "average_response_time": float
    }
  },
  "timestamp": "ISO-8601"
}
```

**Error Responses:**
- `400 Bad Request` - Invalid answer format or missing required fields
- `404 Not Found` - Question or student session not found
- `409 Conflict` - Answer already submitted for this question
- `500 Internal Server Error` - State update failure

---

### 7.2 Backend Processing Workflow

**Step 1: Retrieve Next Question Flow**
```
1. Validate student_id and session_id
2. Fetch student state from PostgreSQL
3. Load prerequisite graph and mastery data
4. Execute sequencing algorithm:
   - Calculate student knowledge state
   - Evaluate mastery thresholds
   - Apply adaptive difficulty rules
   - Select optimal next question
5. Cache question context in Redis (TTL: 300s)
6. Return question with metadata
```

**Step 2: Submit Answer Processing Flow**
```
1. Validate answer submission format
2. Check for duplicate submissions (idempotency)
3. Grade answer against expected response
4. Calculate performance metrics:
   - Correctness classification
   - Response time analysis
   - Difficulty adjustment factor
5. Update Bayesian knowledge state:
   - Recalculate mastery probability
   - Update confidence bounds
   - Evaluate topic mastery criteria
6. Persist updates to PostgreSQL
7. Trigger prerequisite re-evaluation
8. Return updated state and feedback
```

---

### 7.3 State Transition Examples

**Example 1: Correct Answer - Topic Progression**
```
Initial State:
- Topic: "Algebra Basics"
- Mastery: 0.65 (65%)
- Attempts: 8
- Last Correct: 2 questions back

Answer: CORRECT
Response Time: 12 seconds

Result:
- Mastery Updated: 0.65 → 0.72 (Bayesian update)
- Status: In Progress → Ready for Next Topic
- Recommendation: "Proceed to Quadratic Equations"
- Prerequisite Unlock: "Advanced Functions" now available
```

**Example 2: Incorrect Answer - Hint Triggered**
```
Initial State:
- Topic: "Polynomial Division"
- Mastery: 0.42 (42%)
- Streak: Correct × 2
- Hints Available: 3

Answer: INCORRECT
Hint Used: YES (Hint 1)

Result:  
- Mastery Updated: 0.42 → 0.38 (slight decrease)
- Difficulty Adjusted: Current → One Level Easier
- Status: In Progress (maintained)
- Next Question: Similar difficulty with different values
- Hint Remaining: 2
```

---

### 7.4 Query Parameters and Filters

**GET /api/v1/sequencing/student/{student_id}/progress**

Query Parameters:
- `topic` (optional): Filter by specific topic (e.g., "Algebra")
- `start_date` (optional): ISO-8601 date for session filtering
- `end_date` (optional): ISO-8601 date for session filtering
- `include_history` (boolean, default: false): Include detailed attempt history
- `limit` (integer, default: 50): Pagination limit
- `offset` (integer, default: 0): Pagination offset

Example Request:
```
GET /api/v1/sequencing/student/uuid-123/progress?topic=Algebra&include_history=true&limit=100
```

**Response Schema:**
```json
{
  "student_id": "uuid",
  "progress_data": {
    "topics": [
      {
        "name": "string",
        "mastery_level": float,
        "status": "not_started | in_progress | mastered",
        "attempts": integer,
        "timestamp_last_attempt": "ISO-8601"
      }
    ],
    "overall_progress": float,
    "estimated_time_to_completion": integer
  }
}
```

---

### 7.5 Error Handling Strategy

**Validation Errors (400):**
- Missing required fields → Return field-specific error messages
- Type mismatches → Provide expected vs actual type information
- Invalid UUIDs → Reject with validation error

**State Errors (409):**
- Duplicate submissions → Return original response from cache
- Concurrent state updates → Implement optimistic locking with retry logic
- Stale session data → Prompt client to refresh session

**Server Errors (500):**
- Database connection failure → Implement circuit breaker pattern
- Algorithm execution timeout → Return fallback question from cache
- State calculation error → Log error and notify monitoring system

**Client Recovery:**
- Automatic retry with exponential backoff for 5xx errors
- Fallback questions for algorithm failures
- Graceful degradation if hints unavailable

---

**Key Point:**  
This comprehensive API design ensures reliable, efficient sequencing through well-defined endpoints, clear request/response contracts, robust error handling, and transparent state management that enables both immediate question delivery and long-term student progress tracking.


---

## 8. Frontend Requirements

**Essential Components:**
- Question display
- Answer input interface
- Submission button
- Feedback display (correctness, streak, attempts)

**Behavior:**
- Upon submission, the system checks for mastery and retrieves the next question.

**Optional Enhancements:**
- Progress bar
- Concept indicator
- Error-type display

---

## 9. Integration Strategy: Rationale for a Separate Django Application

Given the architectural divergence between Yaksh and the proposed sequencing system, direct integration would introduce significant complexity and maintenance challenges. The adaptive sequencing module is therefore architected as an independent Django application, promoting modularity, maintainability, and scalability.

---

## 9.5 Deployment and DevOps Considerations

### Database Setup and Migrations

**Initial Setup:**
1. Create PostgreSQL database and user for the adaptive sequencing module
2. Run Django migrations to create all tables: `StudentState`, `StudentProgress`, `Question`, `Submission`
3. Load initial question dataset into `Question` table (bulk import from CSV or JSON)
4. Create database indexes as defined in Section 4.7

**Schema Migrations (Future Updates):**
- Use Django's migration framework (`python manage.py makemigrations` and `python manage.py migrate`)
- Zero-downtime migrations using `state_version` field: new code supports both old and new schema versions
- Perform data backups before major migrations

**Backup and Recovery:**
- Automated daily backups of `StudentState`, `StudentProgress`, and `Submission` tables
- Retention: Keep 30 days of backups for compliance and audit purposes
- Recovery plan: Document restore procedure for critical tables

### Environment Configuration

**Required Environment Variables:**
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/adaptive_sequencing
DJANGO_SECRET_KEY=<generate secure key>
YAKSH_API_URL=http://yaksh-main:8000  # Integration with main Yaksh instance
YAKSH_API_KEY=<secure token for Yaksh auth>
DEBUG=False  # Set to False in production
LOG_LEVEL=INFO
```

**Database Connection Pooling:**
- Use `psycopg2-binary` with connection pooling to handle concurrent student sessions
- Recommended: 10-20 pool connections per application instance
- Monitor connection usage; scale horizontally if approaching pool limits

### Deployment Architecture

**Recommended Topology:**
```
┌─────────────────────────────────────────────────────┐
│ Yaksh Frontend (Existing)                           │
└──────────────────┬──────────────────────────────────┘
                   │ HTTP requests
                   ↓
┌──────────────────────────────────────────────────────┐
│ Load Balancer (nginx / AWS ALB)                      │
└──────────┬───────────────────┬──────────────────────┘
           │                   │
    ┌──────↓────────┐  ┌───────↓────────┐
    │ App Instance 1│  │ App Instance 2  │ (scale horizontally)
    │ (Django + API)│  │ (Django + API)  │
    └──────┬────────┘  └───────┬────────┘
           │                   │
           └─────────┬─────────┘
                     ↓
          ┌──────────────────────┐
          │ PostgreSQL Cluster   │
          │ (Primary + Replicas) │
          └──────────────────────┘
```

### Monitoring and Observability

**Key Metrics to Monitor:**
1. **Request Latency:** Time taken for `/next-question` and `/submit-answer` endpoints
   - Target: < 200ms for 95th percentile
2. **State Update Success Rate:** Percentage of submissions that successfully update state
   - Target: > 99.9% success rate
3. **Mastery Achievement Rate:** % of students progressing to next concept
   - Benchmark: Set baseline after initial rollout
4. **Error Rates by Type:** Count of 404, 409, 422 responses
   - Monitor for state corruption or sync issues
5. **Database Performance:**
   - Query times for StudentState retrievals
   - Connection pool utilization
   - Lock contention (for concurrent submissions)

**Logging:**
- Log all state transitions with before/after snapshots (for debugging)
- Log all mastery events with student ID and timestamp
- Log all errors with full context for investigation
- Retention: 90 days of logs

**Alerting:**
- Alert if error rate > 1% for any endpoint
- Alert if request latency > 500ms (95th percentile)
- Alert if database connection pool nearly exhausted
- Alert on failed state migrations or schema version mismatches

### Security and Access Control

**Authentication:**
- Integrate with Yaksh's existing authentication system (OAuth2 or JWT tokens)
- Validate student identity on every API request
- Prevent cross-student state access (isolation)

**Authorization:**
- Students can only access their own state
- Admin endpoints (e.g., force-reset state) require admin authentication
- API keys for question upload/management endpoints

**Data Privacy:**
- Submission records contain student performance data; apply GDPR/privacy policies
- Audit trail of all state mutations for compliance
- Encrypt sensitive fields if required by institutional policy

### Rollout and Testing Strategy

**Pre-Production Testing:**
1. Unit tests for sequencing algorithm (all state transitions, mastery rules, edge cases)
2. Integration tests for API endpoints with mock database
3. Load testing: Simulate 100+ concurrent students; verify latency and correctness
4. Chaos testing: Simulate database failures, slow queries, network delays

**Staged Rollout:**
1. **Phase 1 (Pilot):** Deploy to small group (10-20 students) for 1 week; monitor closely
2. **Phase 2 (Canary):** Roll out to 5% of student base; monitor error rates and mastery completion
3. **Phase 3 (General Availability):** Roll out to all students; maintain 24/7 monitoring
4. **Rollback Plan:** If error rate > 5%, immediately roll back to previous version; investigate root cause

### Scaling Considerations

**Horizontal Scaling (More Instances):**
- Add more application instances behind load balancer as student count grows
- Each instance is stateless; can share database safely
- Monitor database as bottleneck; may need read replicas

**Vertical Scaling (Larger Database):**
- As submission records accumulate (100K+ rows), consider:
  - Archiving old submissions to separate table
  - Adding materialized views for analytics queries
  - Partitioning `Submission` table by date

**Caching (Optional):**
- Cache question sets in-memory (Redis) to reduce database queries for question selection
- Invalidate cache when questions are added/modified
- Cache student state with short TTL (1 minute) to reduce DB load

---

## 10. Benefits

**Educational Advantages:**
- Prevents advancement without addressing weaknesses
- Guarantees mastery before progression
- Adapts dynamically to individual performance

**Technical Advantages:**
- Modular and maintainable architecture
- Scalable and extensible design
- Hybrid stateless and persistent approach

---

## Summary

This proposal presents a definitive, professional approach to integrating adaptive question sequencing into Yaksh. By enforcing mastery, adapting to student performance, and maintaining architectural separation, the system is positioned to deliver substantial educational and technical value.