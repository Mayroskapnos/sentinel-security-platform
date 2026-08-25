from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.detection_rule import DetectionRule
from app.services.rule_loader import RuleLoader, RuleLoadError

VALID_RULE = """
id: DET-TEST-001
name: Test threshold
description: A deterministic test definition.
type: threshold
severity: high
enabled: true
match:
  event_type: authentication
group_by: [source_ip]
threshold:
  count: 2
  timeframe_seconds: 60
suppression_seconds: 30
"""


def test_valid_rule_loads(tmp_path: Path) -> None:
    (tmp_path / "valid.yml").write_text(VALID_RULE, encoding="utf-8")
    rules = RuleLoader(tmp_path).load()
    assert len(rules) == 1
    assert rules[0].rule_id == "DET-TEST-001"
    assert rules[0].threshold is not None


@pytest.mark.parametrize(
    ("contents", "message"),
    [
        ("id: [unterminated", "Unable to load"),
        (VALID_RULE.replace("severity: high", "severity: emergency"), "Invalid detection rule"),
        (VALID_RULE.replace("type: threshold", "type: executable"), "Invalid detection rule"),
        (
            VALID_RULE.replace("threshold:\n  count: 2\n  timeframe_seconds: 60\n", ""),
            "Invalid detection rule",
        ),
    ],
)
def test_invalid_rule_is_rejected(tmp_path: Path, contents: str, message: str) -> None:
    (tmp_path / "invalid.yml").write_text(contents, encoding="utf-8")
    with pytest.raises(RuleLoadError, match=message):
        RuleLoader(tmp_path).load()


def test_duplicate_rule_ids_are_rejected(tmp_path: Path) -> None:
    (tmp_path / "one.yml").write_text(VALID_RULE, encoding="utf-8")
    (tmp_path / "two.yml").write_text(VALID_RULE, encoding="utf-8")
    with pytest.raises(RuleLoadError, match="Duplicate detection rule ID DET-TEST-001"):
        RuleLoader(tmp_path).load()


def test_database_connection_rule_is_intentionally_unmapped() -> None:
    rules = {rule.rule_id: rule for rule in RuleLoader().load()}
    rule = rules["DET-DB-001"]

    assert rule.match.event_type == "database_connection"
    assert rule.match.action is None
    assert rule.match.status is None
    assert rule.context is not None
    assert rule.context.source_asset_type == "workstation"
    assert rule.context.destination_asset_type == "database"
    assert rule.mitre is None


@pytest.mark.asyncio
async def test_sync_clears_removed_database_mitre_mapping(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await RuleLoader().sync(session)
        rule = await session.scalar(
            select(DetectionRule).where(DetectionRule.rule_id == "DET-DB-001")
        )
        assert rule is not None
        rule.mitre_tactic = "Collection"
        rule.mitre_technique_id = "T1213"
        rule.mitre_technique_name = "Data from Information Repositories"
        await session.commit()

        await RuleLoader().sync(session)
        await session.refresh(rule)

        assert rule.mitre_tactic is None
        assert rule.mitre_technique_id is None
        assert rule.mitre_technique_name is None


@pytest.mark.asyncio
async def test_sync_preserves_enabled_state(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await RuleLoader().sync(session)
        rule = await session.scalar(
            select(DetectionRule).where(DetectionRule.rule_id == "DET-SSH-001")
        )
        assert rule is not None
        rule.enabled = False
        await session.commit()
        await RuleLoader().sync(session)
        await session.refresh(rule)
        assert rule.enabled is False
