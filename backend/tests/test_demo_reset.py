from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.cli.demo_reset import reset_demo_data
from app.core.config import Settings
from app.models.asset import Asset
from app.models.detection_rule import DetectionRule
from app.models.scenario_run import ScenarioRun
from app.models.security_event import SecurityEvent


def development_settings() -> Settings:
    return Settings(
        _env_file=None,
        sentinel_env="development",
        database_url="sqlite+aiosqlite://",
    )


@pytest.mark.asyncio
async def test_demo_reset_requires_development_and_explicit_confirmation(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        with pytest.raises(RuntimeError, match="only when SENTINEL_ENV=development"):
            await reset_demo_data(
                session,
                Settings(
                    _env_file=None,
                    sentinel_env="production",
                    database_url="sqlite+aiosqlite://",
                ),
                confirmed=True,
            )
        with pytest.raises(RuntimeError, match="confirm-development-reset"):
            await reset_demo_data(session, development_settings(), confirmed=False)


@pytest.mark.asyncio
async def test_demo_reset_preserves_assets_and_rules_but_clears_activity(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    now = datetime.now(UTC)
    async with session_factory() as session:
        asset = Asset(
            hostname="employee-01",
            display_name="Employee Workstation 01",
            ip_address="10.10.20.10",
            asset_type="workstation",
            operating_system="Linux",
            environment="lab",
            network_zone="user",
            status="online",
            risk_score=87,
            criticality="medium",
            first_seen=now,
            last_seen=now,
        )
        rule = DetectionRule(
            rule_id="DET-TEST-001",
            name="Test rule",
            description="Test rule retained by demo reset.",
            rule_type="single_event",
            severity="low",
            enabled=True,
            event_type="test",
            configuration={},
        )
        run = ScenarioRun(
            scenario_id="SCN-TEST",
            scenario_name="Reset test",
            status="completed",
            total_steps=1,
        )
        session.add_all([asset, rule, run])
        await session.flush()
        session.add(
            SecurityEvent(
                timestamp=now,
                event_type="test",
                source="test",
                hostname=asset.hostname,
                action="observed",
                status="success",
                severity="low",
                raw_event={},
                normalized_data={},
                asset_id=asset.id,
                scenario_run_id=run.id,
                scenario_id=run.scenario_id,
            )
        )
        await session.commit()

        counts = await reset_demo_data(session, development_settings(), confirmed=True)

        assert counts["security_events"] == 1
        assert counts["scenario_runs"] == 1
        assert await session.scalar(select(func.count()).select_from(SecurityEvent)) == 0
        assert await session.scalar(select(func.count()).select_from(ScenarioRun)) == 0
        retained_asset = await session.get(Asset, asset.id)
        assert retained_asset is not None
        assert retained_asset.risk_score == 0
        assert await session.get(DetectionRule, rule.id) is not None
