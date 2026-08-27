import argparse
import asyncio
import logging

from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.db.session import async_session_factory, close_database
from app.models.alert import Alert, AlertEvent
from app.models.asset import Asset
from app.models.incident import Incident, IncidentAlert, IncidentAsset
from app.models.investigation import InvestigationAnalysis, InvestigationMessage
from app.models.network_connection import NetworkConnection
from app.models.scenario_run import ScenarioRun
from app.models.security_event import SecurityEvent

logger = logging.getLogger(__name__)


async def reset_demo_data(
    session: AsyncSession,
    settings: Settings,
    *,
    confirmed: bool,
) -> dict[str, int]:
    """Clear generated demo activity while preserving platform definitions."""
    if settings.sentinel_env.strip().lower() != "development":
        raise RuntimeError("Demo reset is permitted only when SENTINEL_ENV=development.")
    if not confirmed:
        raise RuntimeError("Pass --confirm-development-reset to acknowledge the data removal.")

    models = (
        InvestigationMessage,
        InvestigationAnalysis,
        IncidentAlert,
        IncidentAsset,
        Incident,
        AlertEvent,
        Alert,
        NetworkConnection,
        SecurityEvent,
        ScenarioRun,
    )
    deleted: dict[str, int] = {}
    for model in models:
        result = await session.execute(delete(model))
        deleted[model.__tablename__] = max(result.rowcount or 0, 0)

    reset_assets = await session.execute(update(Asset).values(risk_score=0))
    deleted["asset_risk_scores_reset"] = max(reset_assets.rowcount or 0, 0)
    await session.commit()
    return deleted


async def run(confirmed: bool) -> dict[str, int]:
    try:
        async with async_session_factory() as session:
            return await reset_demo_data(
                session,
                get_settings(),
                confirmed=confirmed,
            )
    finally:
        await close_database()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Clear SENTINEL-generated demo activity while preserving assets, "
            "detection rules, and migrations"
        )
    )
    parser.add_argument(
        "--confirm-development-reset",
        action="store_true",
        help="Acknowledge deletion of development telemetry and investigation data",
    )
    args = parser.parse_args()
    settings = get_settings()
    configure_logging(settings.log_level)
    try:
        counts = asyncio.run(run(confirmed=args.confirm_development_reset))
    except RuntimeError as exc:
        parser.error(str(exc))
    logger.info("Development demo reset complete: %s", counts)


if __name__ == "__main__":
    main()
