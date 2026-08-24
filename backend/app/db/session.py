import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.pool import AsyncAdaptedQueuePool

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    poolclass=AsyncAdaptedQueuePool,
)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def check_database() -> bool:
    """Return whether PostgreSQL accepts a minimal query."""
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except Exception:
        logger.exception("Database health check failed")
        return False


async def close_database() -> None:
    await engine.dispose()
