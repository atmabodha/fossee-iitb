import pytest
import asyncio
import uuid
from typing import List

from api_architecture.database.db import get_db, engine, Base
from api_architecture.services.storage import AsyncQuestionFetcher, create_student_profile, save_student_state
from api_architecture.engine.sequencing_engine import sequence_next_question
from api_architecture.models.student_state import StudentState
from api_architecture.database.models import QuestionRecord
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# We will use vanilla pytest and run the event loop manually to avoid plugin dependency
def test_full_algorithm_backend_integration():
    """
    Test the robust integration of the database storage boundaries,
    the AsyncQuestionFetcher, and the core sequencing algorithm.
    """
    async def run_test():
        # Setup db
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        
        async with AsyncSession(engine) as session:
            q1 = QuestionRecord(concept="C1", error_type="Syntax", question="Fix the syntax error.", test_cases={}, language="python")
            q2 = QuestionRecord(concept="C1", error_type="Logic", question="Fix the logic error.", test_cases={}, language="python")
            q3 = QuestionRecord(concept="C2", error_type="Syntax", question="Next concept question.", test_cases={}, language="python")
            session.add_all([q1, q2, q3])
            await session.commit()

        try:
            async with AsyncSession(engine) as session:
                # 1. Create a fresh student profile
                student_id = uuid.uuid4()
                state: StudentState = await create_student_profile(session, student_id)
                
                assert state is not None
                assert state.student_id == student_id
                assert state.current_concept == "C1"
                assert state.attempts_in_concept == 0
                
                # 2. Instantiate the exact fetcher the platform relies on
                fetcher = AsyncQuestionFetcher(session)
                
                # 3. Pull the first question through the algorithm
                question1 = await sequence_next_question(state, fetcher)
                
                assert question1 is not None
                assert question1.concept == "C1"
                assert question1.error_type == "Syntax"
                
                # 4. Save the modified state back to the database
                await save_student_state(session, state)
                
                # 5. Fetch the next question in sequence
                # Simulate correct answer:
                state.last_answer_correct = True
                state.last_hint_used = False
                
                question2 = await sequence_next_question(state, fetcher)
                assert question2.concept == "C1"
                assert question2.error_type == "Logic"
        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)

    asyncio.run(run_test())


