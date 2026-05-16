import asyncio
import logging
from api_architecture.database.db import engine, Base
# Ensure all models are imported so Base metadata is populated
from api_architecture.database.models import *

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def init_database():
    """Initializes the database schema by dropping and recreating all tables."""
    logger.info("Connecting to database and initializing schema...")
    async with engine.begin() as conn:
        logger.info("Dropping existing tables (if any)...")
        await conn.run_sync(Base.metadata.drop_all)
        
        logger.info("Creating tables...")
        await conn.run_sync(Base.metadata.create_all)
        
    logger.info("Database schema initialized successfully.")

if __name__ == "__main__":
    asyncio.run(init_database())
