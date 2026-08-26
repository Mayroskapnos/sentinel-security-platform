import argparse
import asyncio

from app.db.session import async_session_factory, close_database
from app.services.correlation import CorrelationService


async def rebuild(limit: int) -> None:
    try:
        async with async_session_factory() as session:
            processed, created, updated = await CorrelationService(session).rebuild(limit=limit)
            print(
                f"Processed {processed} unassociated alerts: "
                f"created {created} incidents and updated {updated} incidents."
            )
    finally:
        await close_database()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Non-destructively correlate alerts that do not yet belong to incidents."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5_000,
        help="Maximum number of unassociated alerts to process (default: 5000).",
    )
    arguments = parser.parse_args()
    if not 1 <= arguments.limit <= 100_000:
        parser.error("--limit must be between 1 and 100000")
    asyncio.run(rebuild(arguments.limit))


if __name__ == "__main__":
    main()
