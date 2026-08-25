import asyncio
import logging

from app.core.logging import configure_logging
from app.db.session import async_session_factory, close_database
from app.services.rule_loader import RuleLoader, RuleLoadError

logger = logging.getLogger(__name__)


async def synchronize() -> None:
    try:
        try:
            async with async_session_factory() as session:
                rules = await RuleLoader().sync(session)
            logger.info("rule_sync_complete count=%d", len(rules))
        except RuleLoadError:
            logger.exception("rule_sync_rejected existing database rule state remains available")
    finally:
        await close_database()


def main() -> None:
    configure_logging("INFO")
    asyncio.run(synchronize())


if __name__ == "__main__":
    main()
