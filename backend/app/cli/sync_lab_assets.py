import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import async_session_factory, close_database
from app.lab.assets import LAB_ASSETS
from app.models.asset import Asset

logger = logging.getLogger(__name__)


async def sync_lab_assets() -> int:
    now = datetime.now(UTC)
    async with async_session_factory() as session:
        synchronized = 0
        for definition in LAB_ASSETS:
            asset = await session.scalar(
                select(Asset).where(Asset.hostname == definition["hostname"])
            )
            if asset is None:
                asset = Asset(
                    **definition,
                    first_seen=now,
                    last_seen=now,
                )
                session.add(asset)
            else:
                preserved = {
                    "status": asset.status,
                    "risk_score": asset.risk_score,
                    "first_seen": asset.first_seen,
                    "last_seen": asset.last_seen,
                }
                for field, value in definition.items():
                    if field != "id":
                        setattr(asset, field, value)
                for field, value in preserved.items():
                    setattr(asset, field, value)
            synchronized += 1
        await session.commit()
        logger.info("lab_assets_synchronized count=%d", synchronized)
        return synchronized


async def run() -> None:
    try:
        await sync_lab_assets()
    finally:
        await close_database()


def main() -> None:
    configure_logging(get_settings().log_level)
    asyncio.run(run())


if __name__ == "__main__":
    main()
