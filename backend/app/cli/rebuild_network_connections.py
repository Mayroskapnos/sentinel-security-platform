import argparse
import asyncio

from app.db.session import async_session_factory, close_database
from app.services.network import BACKFILL_EVENT_LIMIT, NetworkService


async def rebuild(limit: int) -> None:
    try:
        async with async_session_factory() as session:
            events, connections = await NetworkService(session).rebuild(limit=limit)
            print(
                f"Rebuilt {connections} network relationships from "
                f"{events} eligible security events."
            )
    finally:
        await close_database()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deterministically rebuild aggregated network relationships."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=BACKFILL_EVENT_LIMIT,
        help="Maximum eligible events allowed before refusing the rebuild.",
    )
    arguments = parser.parse_args()
    if arguments.limit < 1:
        parser.error("--limit must be positive")
    asyncio.run(rebuild(arguments.limit))


if __name__ == "__main__":
    main()
