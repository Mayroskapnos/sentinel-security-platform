from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.alert import Alert, AlertEvent
from app.models.detection_rule import DetectionRule
from app.models.network_connection import NetworkConnection
from app.models.scenario_run import ScenarioRun
from app.models.security_event import SecurityEvent
from tests.factories import asset_payload, event_payload


async def create_assets(client: httpx.AsyncClient) -> tuple[dict, dict]:
    source = (
        await client.post(
            "/api/v1/assets",
            json=asset_payload(hostname="source-host", ip_address="10.10.20.10"),
        )
    ).json()
    destination = (
        await client.post(
            "/api/v1/assets",
            json=asset_payload(
                hostname="destination-host",
                ip_address="10.10.30.10",
                asset_type="server",
                network_zone="server",
                criticality="critical",
                risk_score=72,
            ),
        )
    ).json()
    return source, destination


@pytest.mark.asyncio
async def test_ingestion_creates_and_updates_one_aggregate_relationship(
    client: httpx.AsyncClient,
) -> None:
    source, destination = await create_assets(client)
    latest = datetime.now(UTC)
    payload = event_payload(
        timestamp=latest,
        hostname="source-host",
        source_ip=source["ip_address"],
        destination_ip=destination["ip_address"],
    )
    assert (await client.post("/api/v1/telemetry/events", json=payload)).status_code == 201
    assert (
        await client.post(
            "/api/v1/telemetry/events",
            json={
                **payload,
                "timestamp": (latest - timedelta(minutes=5)).isoformat(),
                "status": "success",
            },
        )
    ).status_code == 201

    response = await client.get("/api/v1/network/connections")
    assert response.status_code == 200
    document = response.json()
    assert document["total"] == 1
    connection = document["items"][0]
    assert connection["connection_count"] == 2
    assert connection["last_status"] == "failed"
    assert connection["source_asset"]["id"] == source["id"]
    assert connection["destination_asset"]["id"] == destination["id"]
    assert connection["first_seen"] == (latest - timedelta(minutes=5)).isoformat().replace(
        "+00:00", "Z"
    )


@pytest.mark.asyncio
async def test_connection_identity_keeps_ports_distinct_and_ignores_unknown_endpoints(
    client: httpx.AsyncClient,
) -> None:
    source, destination = await create_assets(client)
    for port in (22, 2222):
        response = await client.post(
            "/api/v1/telemetry/events",
            json=event_payload(
                hostname="source-host",
                source_ip=source["ip_address"],
                destination_ip=destination["ip_address"],
                destination_port=port,
            ),
        )
        assert response.status_code == 201
    unresolved = await client.post(
        "/api/v1/telemetry/events",
        json=event_payload(
            hostname=None,
            source_ip="192.0.2.10",
            destination_ip=destination["ip_address"],
        ),
    )
    assert unresolved.status_code == 201

    response = await client.get(f"/api/v1/network/connections?source_asset_id={source['id']}")
    assert response.json()["total"] == 2
    assert {item["destination_port"] for item in response.json()["items"]} == {
        22,
        2222,
    }


@pytest.mark.asyncio
async def test_known_ip_aliases_resolve_and_database_sources_share_one_relationship(
    client: httpx.AsyncClient,
) -> None:
    source, destination = await create_assets(client)
    alias = "10.10.20.30"
    updated = await client.patch(
        f"/api/v1/assets/{destination['id']}",
        json={"metadata_json": {"ip_aliases": [alias]}},
    )
    assert updated.status_code == 200
    for normalized_data in (
        {"adapter": "database_client", "service": "postgresql"},
        {"adapter": "postgresql"},
    ):
        response = await client.post(
            "/api/v1/telemetry/events",
            json=event_payload(
                hostname="source-host",
                source_ip=source["ip_address"],
                destination_ip=alias,
                destination_port=5432,
                event_type="database_connection",
                action="database_connect",
                normalized_data=normalized_data,
            ),
        )
        assert response.status_code == 201
    connections = (await client.get("/api/v1/network/connections")).json()
    assert connections["total"] == 1
    assert connections["items"][0]["connection_count"] == 2
    assert connections["items"][0]["connection_type"] == "postgresql"


@pytest.mark.asyncio
async def test_live_topology_returns_assets_observed_edges_and_filters(
    client: httpx.AsyncClient,
) -> None:
    source, destination = await create_assets(client)
    await client.post(
        "/api/v1/telemetry/events",
        json=event_payload(
            hostname="source-host",
            source_ip=source["ip_address"],
            destination_ip=destination["ip_address"],
            normalized_data={"service": "ssh", "protocol": "tcp"},
        ),
    )

    topology = await client.get(f"/api/v1/network/topology?window=1h&asset_id={destination['id']}")
    assert topology.status_code == 200
    document = topology.json()
    assert [node["hostname"] for node in document["nodes"]] == [
        "destination-host",
        "source-host",
    ]
    assert document["nodes"][0]["risk_score"] == 72
    assert document["edges"][0]["source_asset_id"] == source["id"]
    assert document["edges"][0]["destination_asset_id"] == destination["id"]
    assert document["edges"][0]["connection_type"] == "ssh"
    assert document["summary"]["connection_count"] == 1
    assert (await client.get("/api/v1/network/topology?window=invalid")).status_code == 422


@pytest.mark.asyncio
async def test_scenario_topology_uses_only_attributed_events_and_observed_mitre(
    client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    source, destination = await create_assets(client)
    now = datetime.now(UTC)
    async with session_factory() as session:
        run = ScenarioRun(
            scenario_id="SCN-005",
            scenario_name="Enterprise exercise",
            status="completed",
            active_slot=None,
            started_at=now,
            finished_at=now,
            current_step=1,
            total_steps=1,
            steps=[],
            expected_detections=["DET-NET-001", "DET-DB-001"],
            targets=["source-host", "destination-host"],
            result={},
        )
        rule = DetectionRule(
            rule_id="DET-NET-001",
            name="Discovery",
            description="Observed network discovery.",
            rule_type="single_event",
            severity="medium",
            enabled=True,
            event_type="network_connection",
            configuration={},
            mitre_tactic="Discovery",
            mitre_technique_id="T1046",
            mitre_technique_name="Network Service Discovery",
        )
        unmapped_rule = DetectionRule(
            rule_id="DET-DB-001",
            name="Unexpected database connection",
            description="Observed connection evidence only.",
            rule_type="single_event",
            severity="medium",
            enabled=True,
            event_type="database_connection",
            configuration={},
            mitre_tactic=None,
            mitre_technique_id=None,
            mitre_technique_name=None,
        )
        session.add_all([run, rule, unmapped_rule])
        await session.flush()
        attributed_values = event_payload(
            timestamp=now,
            hostname="source-host",
            source_ip=source["ip_address"],
            destination_ip=destination["ip_address"],
            event_type="network_connection",
            action="connection_attempted",
            normalized_data={"service": "ssh", "protocol": "tcp"},
            scenario_run_id=run.id,
            scenario_id=run.scenario_id,
        )
        attributed_values["timestamp"] = now
        attributed = SecurityEvent(**attributed_values, asset_id=UUID(source["id"]))
        unrelated_values = event_payload(
            timestamp=now,
            hostname="source-host",
            source_ip=source["ip_address"],
            destination_ip=destination["ip_address"],
            destination_port=5432,
        )
        unrelated_values["timestamp"] = now
        unrelated = SecurityEvent(**unrelated_values, asset_id=UUID(source["id"]))
        privilege_values = event_payload(
            timestamp=now + timedelta(seconds=1),
            hostname="destination-host",
            source_ip=destination["ip_address"],
            destination_ip=None,
            source_port=None,
            destination_port=None,
            event_type="privilege",
            action="sudo_command",
            normalized_data={"privileged": True},
            scenario_run_id=run.id,
            scenario_id=run.scenario_id,
        )
        privilege_values["timestamp"] = now + timedelta(seconds=1)
        privilege = SecurityEvent(**privilege_values, asset_id=UUID(destination["id"]))
        session.add_all([attributed, unrelated, privilege])
        await session.flush()
        alert = Alert(
            timestamp=now,
            title="Discovery",
            description="Observed network discovery.",
            severity="medium",
            status="new",
            detection_rule_id=rule.id,
            asset_id=UUID(destination["id"]),
            source_ip=source["ip_address"],
            destination_ip=destination["ip_address"],
            risk_score=55,
            mitre_tactic="Discovery",
            mitre_technique_id="T1046",
            mitre_technique_name="Network Service Discovery",
            evidence={"event_count": 1},
            metadata_json={},
            deduplication_key="scenario-test",
            first_event_at=now,
            last_event_at=now,
        )
        session.add(alert)
        await session.flush()
        unmapped_alert = Alert(
            timestamp=now + timedelta(seconds=1),
            title="Unexpected database connection",
            description="Observed connection evidence only.",
            severity="medium",
            status="new",
            detection_rule_id=unmapped_rule.id,
            asset_id=UUID(destination["id"]),
            source_ip=source["ip_address"],
            destination_ip=destination["ip_address"],
            risk_score=50,
            mitre_tactic=None,
            mitre_technique_id=None,
            mitre_technique_name=None,
            evidence={"event_count": 1},
            metadata_json={},
            deduplication_key="unmapped-scenario-test",
            first_event_at=now + timedelta(seconds=1),
            last_event_at=now + timedelta(seconds=1),
        )
        session.add(unmapped_alert)
        await session.flush()
        session.add_all(
            [
                AlertEvent(alert_id=alert.id, event_id=attributed.id),
                AlertEvent(alert_id=unmapped_alert.id, event_id=privilege.id),
            ]
        )
        await session.commit()
        run_id = run.id

    response = await client.get(f"/api/v1/network/topology?scenario_run_id={run_id}&window=5m")
    assert response.status_code == 200
    document = response.json()
    assert document["scenario"]["run_id"] == str(run_id)
    assert document["scenario"]["event_count"] == 2
    assert document["scenario"]["alert_count"] == 2
    assert len(document["edges"]) == 1
    assert document["edges"][0]["destination_port"] == 22
    assert [item["action"] for item in document["activities"]] == [
        "connection_attempted",
        "sudo_command",
    ]
    assert len(document["alerts"]) == 2
    assert document["observed_techniques"] == [
        {
            "technique_id": "T1046",
            "technique_name": "Network Service Discovery",
            "tactic": "Discovery",
            "alert_ids": [document["alerts"][0]["id"]],
        }
    ]


@pytest.mark.asyncio
async def test_rebuild_is_deterministic_and_does_not_modify_events(
    client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    source, destination = await create_assets(client)
    await client.post(
        "/api/v1/telemetry/events",
        json=event_payload(
            hostname="source-host",
            source_ip=source["ip_address"],
            destination_ip=destination["ip_address"],
        ),
    )
    from app.services.network import NetworkService

    async with session_factory() as session:
        before = int(await session.scalar(select(func.count(SecurityEvent.id))) or 0)
        first = await NetworkService(session).rebuild()
        second = await NetworkService(session).rebuild()
        after = int(await session.scalar(select(func.count(SecurityEvent.id))) or 0)
        relationships = int(await session.scalar(select(func.count(NetworkConnection.id))) or 0)
    assert first == second == (1, 1)
    assert before == after == 1
    assert relationships == 1
