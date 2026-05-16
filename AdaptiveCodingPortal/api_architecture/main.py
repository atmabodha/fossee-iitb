"""
FastAPI application entry point.

Starts the uvicorn server, loads the question bank from CSV,
and registers all API routes.

Run with:  python -m uvicorn api_architecture.main:app --reload
"""

import logging

from fastapi import FastAPI, Depends
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from api_architecture.database.db import get_db, engine
from sqlalchemy.ext.asyncio import AsyncSession
from api_architecture.database.db import get_db, engine
from fastapi.middleware.cors import CORSMiddleware

from api_architecture.api.routes import router
from api_architecture.api.middleware import StatelessAPIMiddleware, RequestLoggingMiddleware
from api_architecture.database.models import Base

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(_app):
    """Lifespan event handler for FastAPI app."""
    logger.info("Starting up DB connection and creating tables if missing...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Startup complete.")
    yield

app = FastAPI(
    title="Question Sequencing Algorithm API",
    description=(
        "Backend API for the adaptive question sequencing system. "
        "Determines which programming question a student should see next."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow all origins during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Stateless API middleware — adds logging, state validation, and metrics
app.add_middleware(StatelessAPIMiddleware)

# Request logging middleware — logs all requests/responses
app.add_middleware(RequestLoggingMiddleware)

# Register API routes
app.include_router(router)


# ---------------------------------------------------------------------------
# Startup: load questions from CSV into memory
# ---------------------------------------------------------------------------

# Startup logic moved to lifespan event handler above.


@app.get("/")
async def root(db: AsyncSession = Depends(get_db)):
    """Health-check endpoint."""
    from api_architecture.services.storage import get_loaded_question_count
    from sqlalchemy.ext.asyncio import AsyncSession
    from fastapi import Depends
    from api_architecture.database.db import get_db
    from sqlalchemy.ext.asyncio import AsyncSession
    from fastapi import Depends
    from api_architecture.database.db import get_db

    return {
        "status": "ok",
        "service": "Question Sequencing Algorithm API",
        "questions_loaded": await get_loaded_question_count(db),
    }
