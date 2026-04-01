"""Database initialisation helpers."""

import logging

from sqlalchemy.ext.asyncio import create_async_engine

from src.core.config import settings

# Import every model so that their table definitions are registered
# against Base.metadata before we call create_all.
import src.models  # noqa: F401 – side-effect import
from src.models.base import Base

logger = logging.getLogger(__name__)


async def init_db() -> None:
    """Create all database tables if they do not already exist.

    This function is idempotent: SQLAlchemy's ``create_all`` uses
    ``CREATE TABLE IF NOT EXISTS`` semantics, so it is safe to call on
    every application startup.
    """
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created / verified successfully")
    finally:
        await engine.dispose()
