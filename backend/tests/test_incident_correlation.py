import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.alert import Alert
from app.models.asset import Asset
from app.models.detection_rule import DetectionRule
from app.models.enums import AlertStatus
from app.models.incident import Incident, IncidentAlert
from app.models.network_connection import NetworkConnection
from app.models.scenario_run import ScenarioRun
from app.models.security_event import SecurityEvent
from app.services.correlation import CorrelationService
from app.services.incidents import IncidentService

MITRE_BY_RULE = {
    "DET-SSH-001": ("Credential Access", "T1110", "Brute Force"),
    "DET-SSH-002": ("Defense Evasion", "T1078", "Valid Accounts"),
    "DET-NET-001": ("Discovery", "T1046", "Network Service Discovery"),
    "DET-PRIV-001": (
        "Privilege Escalation",
        "T1548.003",
        "Sudo and Sudo Caching",
    ),
}


async def make_asset(
    session: AsyncSession,
    hostname: str,
    ip_address: str,
    *,
    criticality: str = "medium",
) -> Asset:
    observed = datetime(2026, 8, 26, 10, tzinfo=UTC)
    asset = Asset(
        hostname=hostname,
        display_name=hostname.replace("-", " ").title(),
        ip_address=ip_address,
        asset_type="workstation",
        operating_system="Linux",
        environment="test",
        network_zone="employee",
        status="online",
        risk_score=0,
        criticality=criticality,
        first_seen=observed,
        last_seen=observed,
        metadata_json={},
    )
    session.add(asset)
    await session.flush()
    return asset


async def make_scenario(session: AsyncSession, scenario_id: str) -> ScenarioRun:
    observed = datetime(2026, 8, 26, 10, tzinfo=UTC)
    run = ScenarioRun(
        scenario_id=scenario_id,
        scenario_name=f"{scenario_id} test",
        status="completed",
        active_slot=None,
        started_at=observed,
        finished_at=observed + timedelta(minutes=1),
        current_step=1,
        total_steps=1,
        steps=[],
        expected_detections=[],
        targets=[],
        result={},
    )
    session.add(run)
    await session.flush()
    return run


async def make_alert(
    session: AsyncSession,
    *,
    rule_id: str,
    observed_at: datetime,
    asset: Asset,
    source_ip: str,
    username: str,
    scenario_run_id: UUID | None = None,
    destination_ip: str | None = None,
    severity: str = "high",
    event_type: str = "authentication",
    action: str = "ssh_login",
    event_status: str = "failed",
) -> Alert:
    mitre = MITRE_BY_RULE.get(rule_id)
    rule = DetectionRule(
        rule_id=rule_id,
        name=rule_id,
        description="Test rule",
        rule_type="single_event",
        severity=severity,
        enabled=True,
        event_type=event_type,
        configuration={},
        mitre_tactic=mitre[0] if mitre else None,
        mitre_technique_id=mitre[1] if mitre else None,
        mitre_technique_name=mitre[2] if mitre else None,
    )
    event = SecurityEvent(
        timestamp=observed_at,
        event_type=event_type,
        source="test",
        source_ip=source_ip,
        destination_ip=destination_ip or asset.ip_address,
        source_port=44000,
        destination_port=22,
        hostname=asset.hostname,
        username=username,
        process_name="sshd",
        action=action,
        status=event_status,
        severity=severity,
        raw_event={},
        normalized_data={"service": "ssh"},
        asset_id=asset.id,
        scenario_run_id=scenario_run_id,
        scenario_id=None,
    )
    alert = Alert(
        timestamp=observed_at,
        title=rule_id,
        description="Evidence-backed test alert",
        severity=severity,
        status="new",
        detection_rule=rule,
        asset=asset,
        source_ip=source_ip,
        destination_ip=event.destination_ip,
        username=username,
        risk_score=65,
        mitre_tactic=rule.mitre_tactic,
        mitre_technique_id=rule.mitre_technique_id,
        mitre_technique_name=rule.mitre_technique_name,
        evidence={"event_count": 1},
        metadata_json={},
        deduplication_key=f"{rule_id}:{source_ip}:{observed_at.isoformat()}",
        first_event_at=observed_at,
        last_event_at=observed_at,
        evidence_events=[event],
        incident_link=None,
    )
    session.add(alert)
    await session.commit()
    return alert


@pytest.mark.asyncio
async def test_related_auth_alerts_form_one_explainable_incident(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        asset = await make_asset(session, "employee-01", "10.10.20.10")
        start = datetime(2026, 8, 26, 10, tzinfo=UTC)
        brute_force = await make_alert(
            session,
            rule_id="DET-SSH-001",
            observed_at=start,
            asset=asset,
            source_ip="10.10.50.2",
            username="demo-user",
        )
        created = await CorrelationService(session).process_alert(brute_force.id)
        success = await make_alert(
            session,
            rule_id="DET-SSH-002",
            observed_at=start + timedelta(seconds=20),
            asset=asset,
            source_ip="10.10.50.2",
            username="demo-user",
        )
        updated = await CorrelationService(session).process_alert(success.id)

        assert created.created is True
        assert updated.created is False
        assert updated.incident.id == created.incident.id
        assert updated.incident.alert_count == 2
        assert updated.incident.confidence_score == 80
        detail = await clientless_detail(session, updated.incident.id)
        assert [item.rule_id for item in detail.alerts] == ["DET-SSH-001", "DET-SSH-002"]
        assert [item.stage for item in detail.story] == [
            "credential_activity",
            "authenticated_access",
        ]
        assert detail.title == "Possible Credential Compromise"
        assert {item.type for item in detail.correlation_signals} >= {
            "shared_source_ip",
            "shared_username",
            "shared_asset",
            "detection_progression",
            "time_proximity",
        }

        duplicate = await CorrelationService(session).process_alert(success.id)
        assert duplicate.created is False
        assert duplicate.incident.alert_count == 2
        assert await session.scalar(select(func.count(IncidentAlert.alert_id))) == 2

        brute_force.status = AlertStatus.RESOLVED
        success.status = AlertStatus.RESOLVED
        await session.commit()
        resolved = await IncidentService(session).recalculate(updated.incident.id)
        assert resolved.risk_score == 35
        assert resolved.severity == "low"


async def clientless_detail(session: AsyncSession, incident_id: UUID):
    from app.services.incidents import IncidentService

    return await IncidentService(session).get(incident_id)


@pytest.mark.asyncio
async def test_unrelated_sources_and_assets_do_not_merge_when_only_time_is_shared(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        first_asset = await make_asset(session, "employee-01", "10.10.20.10")
        second_asset = await make_asset(session, "employee-02", "10.10.20.11")
        start = datetime(2026, 8, 26, 10, tzinfo=UTC)
        first = await make_alert(
            session,
            rule_id="DET-SSH-001-A",
            observed_at=start,
            asset=first_asset,
            source_ip="10.10.50.2",
            username="alice",
        )
        second = await make_alert(
            session,
            rule_id="DET-SSH-001-B",
            observed_at=start + timedelta(seconds=5),
            asset=second_asset,
            source_ip="10.10.50.3",
            username="bob",
        )
        first_outcome = await CorrelationService(session).process_alert(first.id)
        second_outcome = await CorrelationService(session).process_alert(second.id)
        assert first_outcome.incident.id != second_outcome.incident.id
        assert await session.scalar(select(func.count(Incident.id))) == 2


@pytest.mark.asyncio
async def test_alert_outside_window_does_not_merge_even_with_shared_identity(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        asset = await make_asset(session, "employee-01", "10.10.20.10")
        start = datetime(2026, 8, 26, 10, tzinfo=UTC)
        first = await make_alert(
            session,
            rule_id="DET-SSH-001-A",
            observed_at=start,
            asset=asset,
            source_ip="10.10.50.2",
            username="alice",
        )
        second = await make_alert(
            session,
            rule_id="DET-SSH-001-B",
            observed_at=start + timedelta(minutes=16),
            asset=asset,
            source_ip="10.10.50.2",
            username="alice",
        )
        first_outcome = await CorrelationService(session).process_alert(first.id)
        second_outcome = await CorrelationService(session).process_alert(second.id)
        assert first_outcome.incident.id != second_outcome.incident.id


@pytest.mark.asyncio
async def test_observed_network_relationship_contributes_without_shared_asset(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        first_asset = await make_asset(session, "employee-01", "10.10.20.10")
        second_asset = await make_asset(session, "admin-server", "10.10.30.10")
        start = datetime(2026, 8, 26, 10, tzinfo=UTC)
        first = await make_alert(
            session,
            rule_id="DET-SSH-001-A",
            observed_at=start,
            asset=first_asset,
            source_ip="10.10.50.2",
            username="alice",
        )
        session.add(
            NetworkConnection(
                relationship_key="test-network-relationship",
                source_asset_id=first_asset.id,
                destination_asset_id=second_asset.id,
                source_ip=first_asset.ip_address,
                destination_ip=second_asset.ip_address,
                source_port=44000,
                destination_port=22,
                protocol="tcp",
                connection_type="ssh",
                first_seen=start,
                last_seen=start,
                connection_count=1,
                last_status="success",
                metadata_json={},
            )
        )
        await session.commit()
        second = await make_alert(
            session,
            rule_id="DET-SSH-001-B",
            observed_at=start + timedelta(seconds=10),
            asset=second_asset,
            source_ip="10.10.50.2",
            username="alice",
        )
        first_outcome = await CorrelationService(session).process_alert(first.id)
        second_outcome = await CorrelationService(session).process_alert(second.id)
        assert first_outcome.incident.id == second_outcome.incident.id
        detail = await clientless_detail(session, second_outcome.incident.id)
        assert {item.type for item in detail.correlation_signals} >= {
            "shared_source_ip",
            "shared_username",
            "observed_network_relationship",
            "time_proximity",
        }
        assert "shared_asset" not in {item.type for item in detail.correlation_signals}


@pytest.mark.asyncio
async def test_duplicate_concurrent_correlation_is_idempotent(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as setup_session:
        asset = await make_asset(setup_session, "employee-01", "10.10.20.10")
        alert = await make_alert(
            setup_session,
            rule_id="DET-SSH-001",
            observed_at=datetime(2026, 8, 26, 10, tzinfo=UTC),
            asset=asset,
            source_ip="10.10.50.2",
            username="alice",
        )

    async def correlate_once():
        async with session_factory() as session:
            return await CorrelationService(session).process_alert(alert.id)

    first, second = await asyncio.gather(correlate_once(), correlate_once())
    assert {first.incident.id, second.incident.id} == {first.incident.id}
    assert sorted([first.created, second.created]) == [False, True]
    async with session_factory() as session:
        assert await session.scalar(select(func.count(Incident.id))) == 1
        assert await session.scalar(select(func.count(IncidentAlert.alert_id))) == 1


@pytest.mark.asyncio
async def test_shared_scenario_correlates_but_different_explicit_scenarios_do_not(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        asset_a = await make_asset(session, "employee-01", "10.10.20.10")
        asset_b = await make_asset(session, "employee-02", "10.10.20.11")
        shared = await make_scenario(session, "SCN-005")
        other = await make_scenario(session, "SCN-001")
        start = datetime(2026, 8, 26, 10, tzinfo=UTC)
        first = await make_alert(
            session,
            rule_id="DET-SSH-001-A",
            observed_at=start,
            asset=asset_a,
            source_ip="10.10.50.2",
            username="alice",
            scenario_run_id=shared.id,
        )
        second = await make_alert(
            session,
            rule_id="DET-SSH-001-B",
            observed_at=start + timedelta(seconds=15),
            asset=asset_b,
            source_ip="10.10.50.3",
            username="bob",
            scenario_run_id=shared.id,
        )
        third = await make_alert(
            session,
            rule_id="DET-SSH-001-C",
            observed_at=start + timedelta(seconds=20),
            asset=asset_a,
            source_ip="10.10.50.2",
            username="alice",
            scenario_run_id=other.id,
        )
        first_outcome = await CorrelationService(session).process_alert(first.id)
        second_outcome = await CorrelationService(session).process_alert(second.id)
        third_outcome = await CorrelationService(session).process_alert(third.id)
        assert first_outcome.incident.id == second_outcome.incident.id
        assert first_outcome.incident.id != third_outcome.incident.id


@pytest.mark.asyncio
async def test_scn_005_story_is_deterministic_conservative_and_unmapped_for_database(
    client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        employee = await make_asset(session, "employee-01", "10.10.20.10")
        web = await make_asset(session, "web-server", "10.10.10.10", criticality="high")
        admin = await make_asset(session, "admin-server", "10.10.30.10", criticality="critical")
        database = await make_asset(session, "database", "10.10.30.20", criticality="critical")
        run = await make_scenario(session, "SCN-005")
        start = datetime(2026, 8, 26, 10, tzinfo=UTC)
        definitions = (
            (
                "DET-SSH-001",
                employee,
                "10.10.50.2",
                employee.ip_address,
                "authentication",
                "ssh_login",
                "failed",
                "high",
            ),
            (
                "DET-SSH-002",
                employee,
                "10.10.50.2",
                employee.ip_address,
                "authentication",
                "ssh_login",
                "success",
                "high",
            ),
            (
                "DET-NET-001",
                web,
                employee.ip_address,
                web.ip_address,
                "network_connection",
                "connection_attempted",
                "failed",
                "medium",
            ),
            (
                "DET-PRIV-001",
                admin,
                employee.ip_address,
                admin.ip_address,
                "privilege",
                "sudo_command",
                "success",
                "high",
            ),
            (
                "DET-DB-001",
                database,
                employee.ip_address,
                database.ip_address,
                "database_connection",
                "database_connect",
                "success",
                "medium",
            ),
        )
        outcomes = []
        for index, definition in enumerate(definitions):
            (
                rule_id,
                asset,
                source_ip,
                destination_ip,
                event_type,
                action,
                event_status,
                severity,
            ) = definition
            alert = await make_alert(
                session,
                rule_id=rule_id,
                observed_at=start + timedelta(seconds=index * 10),
                asset=asset,
                source_ip=source_ip,
                destination_ip=destination_ip,
                username="admin-demo",
                scenario_run_id=run.id,
                severity=severity,
                event_type=event_type,
                action=action,
                event_status=event_status,
            )
            outcomes.append(await CorrelationService(session).process_alert(alert.id))

        assert len({outcome.incident.id for outcome in outcomes}) == 1
        detail = await IncidentService(session).get(outcomes[-1].incident.id)
        assert detail.alert_count == 5
        assert detail.asset_count == 4
        assert detail.event_count == 5
        assert detail.confidence_score == 99
        assert detail.risk_score == 100
        assert detail.severity == "critical"
        assert detail.title == "Possible Credential Compromise and Internal Movement"
        assert [item.stage for item in detail.story] == [
            "credential_activity",
            "authenticated_access",
            "discovery",
            "privilege_activity",
            "database_access",
        ]
        assert [item.technique_id for item in detail.observed_techniques] == [
            "T1110",
            "T1078",
            "T1046",
            "T1548.003",
        ]
        database_story = detail.story[-1]
        assert database_story.mitre_technique_id is None
        assert "connection" in database_story.description.lower()
        conservative_text = " ".join(item.description.lower() for item in detail.story)
        for unsupported_claim in (
            "credential stolen",
            "data exfiltrated",
            "host compromised",
            "data queried",
        ):
            assert unsupported_claim not in conservative_text

    incident_id = outcomes[-1].incident.id
    invalid = await client.patch(f"/api/v1/incidents/{incident_id}", json={"status": "contained"})
    assert invalid.status_code == 409
    for status in ("investigating", "contained", "resolved"):
        updated = await client.patch(f"/api/v1/incidents/{incident_id}", json={"status": status})
        assert updated.status_code == 200
        assert updated.json()["status"] == status

    async with session_factory() as session:
        employee = await session.scalar(select(Asset).where(Asset.hostname == "employee-01"))
        assert employee is not None
        later = await make_alert(
            session,
            rule_id="DET-SSH-001-LATER",
            observed_at=start + timedelta(minutes=1),
            asset=employee,
            source_ip="10.10.50.2",
            username="admin-demo",
            scenario_run_id=run.id,
        )
        later_outcome = await CorrelationService(session).process_alert(later.id)
        assert later_outcome.incident.id != incident_id


@pytest.mark.asyncio
async def test_incident_api_filters_status_false_positive_and_incident_topology(
    client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        asset = await make_asset(session, "employee-01", "10.10.20.10")
        alert = await make_alert(
            session,
            rule_id="DET-DB-001",
            observed_at=datetime(2026, 8, 26, 10, tzinfo=UTC),
            asset=asset,
            source_ip="10.10.20.10",
            destination_ip="10.10.30.20",
            username="demo-user",
        )
        outcome = await CorrelationService(session).process_alert(alert.id)

    queue = await client.get("/api/v1/incidents", params={"asset_id": str(asset.id)})
    assert queue.status_code == 200
    assert queue.json()["total"] == 1
    detail = (await client.get(f"/api/v1/incidents/{outcome.incident.id}")).json()
    assert detail["observed_techniques"] == []
    assert "connection" in detail["story"][0]["description"].lower()
    assert "query" not in detail["story"][0]["description"].lower()

    topology = await client.get(
        "/api/v1/network/topology",
        params={"incident_id": str(outcome.incident.id), "window": "all"},
    )
    assert topology.status_code == 200
    assert topology.json()["incident"]["incident_number"].startswith("INC-")
    assert topology.json()["alerts"][0]["id"] == str(alert.id)
    assert (
        await client.get(
            "/api/v1/network/topology",
            params={
                "incident_id": str(outcome.incident.id),
                "scenario_run_id": str(outcome.incident.id),
            },
        )
    ).status_code == 422

    updated = await client.patch(f"/api/v1/alerts/{alert.id}", json={"status": "false_positive"})
    assert updated.status_code == 200
    refreshed = (await client.get(f"/api/v1/incidents/{outcome.incident.id}")).json()
    assert refreshed["status"] == "false_positive"
    assert refreshed["risk_score"] == 0
