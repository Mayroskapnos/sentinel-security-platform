from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.realtime.manager import websocket_manager
from app.schemas.realtime import AlertCreatedMessage, AlertUpdatedMessage
from app.services.risk import RiskService
from app.services.rule_loader import RuleLoader
from tests.factories import asset_payload, event_payload


async def sync_rules(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        await RuleLoader().sync(session)


async def create_asset(client: httpx.AsyncClient, **overrides) -> dict:
    response = await client.post("/api/v1/assets", json=asset_payload(**overrides))
    assert response.status_code == 201
    return response.json()


async def send_failures(
    client: httpx.AsyncClient,
    count: int,
    start: datetime,
    *,
    source_ip: str = "10.10.50.2",
    spacing_seconds: int = 1,
    username: str = "demo-user",
) -> None:
    for index in range(count):
        response = await client.post(
            "/api/v1/telemetry/events",
            json=event_payload(
                timestamp=start + timedelta(seconds=index * spacing_seconds),
                source_ip=source_ip,
                username=username,
            ),
        )
        assert response.status_code == 201


@pytest.mark.asyncio
async def test_ssh_threshold_creates_one_evidence_backed_alert_and_updates_risk(
    client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await sync_rules(session_factory)
    asset = await create_asset(client)
    await send_failures(client, 10, datetime(2026, 8, 24, 12, tzinfo=UTC))

    alerts = (await client.get("/api/v1/alerts?rule_id=DET-SSH-001")).json()
    assert alerts["total"] == 1
    alert = alerts["items"][0]
    assert alert["severity"] == "high"
    assert alert["evidence_count"] == 10
    assert alert["asset"]["id"] == asset["id"]
    assert alert["evidence"]["observed_count"] == 10
    detail = (await client.get(f"/api/v1/alerts/{alert['id']}")).json()
    assert len(detail["evidence_events"]) == 10
    assert {event["id"] for event in detail["evidence_events"]}
    refreshed_asset = (await client.get(f"/api/v1/assets/{asset['id']}")).json()
    assert refreshed_asset["risk_score"] == 45


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("count", "spacing", "sources"),
    [
        (9, 1, ["10.10.50.2"] * 9),
        (10, 140, ["10.10.50.2"] * 10),
        (10, 1, ["10.10.50.2"] * 5 + ["10.10.50.3"] * 5),
    ],
)
async def test_ssh_threshold_negative_cases(
    client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    count: int,
    spacing: int,
    sources: list[str],
) -> None:
    await sync_rules(session_factory)
    await create_asset(client)
    start = datetime(2026, 8, 24, 12, tzinfo=UTC)
    for index in range(count):
        response = await client.post(
            "/api/v1/events",
            json=event_payload(
                timestamp=start + timedelta(seconds=index * spacing),
                source_ip=sources[index],
            ),
        )
        assert response.status_code == 201
    assert (await client.get("/api/v1/alerts?rule_id=DET-SSH-001")).json()["total"] == 0


@pytest.mark.asyncio
async def test_success_after_failures_requires_same_group(
    client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await sync_rules(session_factory)
    await create_asset(client)
    start = datetime(2026, 8, 24, 12, tzinfo=UTC)
    isolated_success = await client.post(
        "/api/v1/events",
        json=event_payload(timestamp=start - timedelta(seconds=1), status="success"),
    )
    assert isolated_success.status_code == 201
    assert (await client.get("/api/v1/alerts?rule_id=DET-SSH-002")).json()["total"] == 0
    await send_failures(client, 5, start)
    success = await client.post(
        "/api/v1/events",
        json=event_payload(timestamp=start + timedelta(seconds=10), status="success"),
    )
    assert success.status_code == 201
    alerts = (await client.get("/api/v1/alerts?rule_id=DET-SSH-002")).json()
    assert alerts["total"] == 1
    assert alerts["items"][0]["evidence_count"] == 6

    mismatched = await client.post(
        "/api/v1/events",
        json=event_payload(
            timestamp=start + timedelta(seconds=11), status="success", username="other-user"
        ),
    )
    assert mismatched.status_code == 201
    assert (await client.get("/api/v1/alerts?rule_id=DET-SSH-002")).json()["total"] == 1


@pytest.mark.asyncio
async def test_suppression_updates_alert_then_expires(
    client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await sync_rules(session_factory)
    await create_asset(client)
    start = datetime(2026, 8, 24, 12, tzinfo=UTC)
    await send_failures(client, 12, start)
    alerts = (await client.get("/api/v1/alerts?rule_id=DET-SSH-001")).json()
    assert alerts["total"] == 1
    assert alerts["items"][0]["evidence_count"] == 12
    assert alerts["items"][0]["evidence"]["suppressed_matches"] == 2

    await send_failures(client, 10, start + timedelta(seconds=360))
    assert (await client.get("/api/v1/alerts?rule_id=DET-SSH-001")).json()["total"] == 2


@pytest.mark.asyncio
async def test_remaining_bundled_rules_trigger_deterministically(
    client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await sync_rules(session_factory)
    await create_asset(client, hostname="employee-01", ip_address="10.10.20.10")
    await create_asset(
        client,
        hostname="database-01",
        ip_address="10.10.30.20",
        mac_address="02:42:0a:0a:14:33",
        asset_type="database",
        network_zone="data",
    )
    start = datetime(2026, 8, 24, 12, tzinfo=UTC)
    for port in range(20, 30):
        response = await client.post(
            "/api/v1/events",
            json=event_payload(
                timestamp=start + timedelta(seconds=port - 20),
                event_type="network_connection",
                action="connect",
                status="success",
                destination_port=port,
                hostname=None,
            ),
        )
        assert response.status_code == 201
    privilege = await client.post(
        "/api/v1/events",
        json=event_payload(
            timestamp=start,
            event_type="privilege",
            action="sudo_command",
            status="success",
        ),
    )
    database = await client.post(
        "/api/v1/events",
        json=event_payload(
            timestamp=start,
            event_type="database_connection",
            action="database_connect",
            status="success",
            source_ip="10.10.20.10",
            destination_ip="10.10.30.20",
            hostname=None,
        ),
    )
    assert privilege.status_code == database.status_code == 201
    alerts = (await client.get("/api/v1/alerts?page_size=100")).json()["items"]
    assert {alert["detection_rule"]["rule_id"] for alert in alerts} >= {
        "DET-NET-001",
        "DET-PRIV-001",
        "DET-DB-001",
    }


@pytest.mark.asyncio
async def test_rule_api_disable_and_reenable_controls_future_evaluation(
    client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await sync_rules(session_factory)
    await create_asset(client)
    rules = (await client.get("/api/v1/rules?search=DET-SSH-001")).json()
    rule = rules["items"][0]
    assert (await client.get(f"/api/v1/rules/{rule['id']}")).status_code == 200
    disabled = await client.patch(f"/api/v1/rules/{rule['id']}", json={"enabled": False})
    assert disabled.status_code == 200
    await send_failures(client, 10, datetime(2026, 8, 24, 12, tzinfo=UTC))
    assert (await client.get("/api/v1/alerts?rule_id=DET-SSH-001")).json()["total"] == 0

    enabled = await client.patch(f"/api/v1/rules/{rule['id']}", json={"enabled": True})
    assert enabled.status_code == 200
    await send_failures(
        client,
        10,
        datetime(2026, 8, 24, 13, tzinfo=UTC),
        source_ip="10.10.50.9",
    )
    assert (await client.get("/api/v1/alerts?rule_id=DET-SSH-001")).json()["total"] == 1


@pytest.mark.asyncio
async def test_alert_workflow_filters_pagination_and_risk_recalculation(
    client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await sync_rules(session_factory)
    asset = await create_asset(client)
    await send_failures(client, 10, datetime(2026, 8, 24, 12, tzinfo=UTC))
    page = (await client.get("/api/v1/alerts?severity=high&status=new&page_size=1")).json()
    assert page["total"] == 1
    assert page["page_size"] == 1
    alert_id = page["items"][0]["id"]
    assert (
        await client.get("/api/v1/alerts/00000000-0000-0000-0000-000000000000")
    ).status_code == 404
    investigating = await client.patch(
        f"/api/v1/alerts/{alert_id}", json={"status": "investigating"}
    )
    assert investigating.status_code == 200
    resolved = await client.patch(f"/api/v1/alerts/{alert_id}", json={"status": "resolved"})
    assert resolved.status_code == 200
    invalid = await client.patch(f"/api/v1/alerts/{alert_id}", json={"status": "new"})
    assert invalid.status_code == 409
    refreshed_asset = (await client.get(f"/api/v1/assets/{asset['id']}")).json()
    assert refreshed_asset["risk_score"] == 25


@pytest.mark.asyncio
async def test_multiple_active_alerts_add_deterministic_weight(
    client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await sync_rules(session_factory)
    asset = await create_asset(client)
    baseline = (await client.get(f"/api/v1/assets/{asset['id']}")).json()
    assert baseline["risk_score"] == 25
    start = datetime(2026, 8, 24, 12, tzinfo=UTC)
    await send_failures(client, 10, start, source_ip="10.10.50.20")
    await send_failures(client, 10, start, source_ip="10.10.50.21")
    elevated = (await client.get(f"/api/v1/assets/{asset['id']}")).json()
    assert elevated["risk_score"] == 65
    alerts = (await client.get("/api/v1/alerts?rule_id=DET-SSH-001")).json()["items"]
    await client.patch(f"/api/v1/alerts/{alerts[0]['id']}", json={"status": "resolved"})
    reduced = (await client.get(f"/api/v1/assets/{asset['id']}")).json()
    assert reduced["risk_score"] == 45


def test_alert_priority_score_is_bounded() -> None:
    assert RiskService.alert_score("critical", "critical", 10_000) == 100
    assert RiskService.alert_score("informational", "low", 1) == 5


@pytest.mark.asyncio
async def test_alert_websocket_messages_use_persistent_alert_id(
    client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await sync_rules(session_factory)
    await create_asset(client)
    broadcast = AsyncMock()
    monkeypatch.setattr(websocket_manager, "broadcast", broadcast)
    await send_failures(client, 11, datetime(2026, 8, 24, 12, tzinfo=UTC))
    messages = [call.args[0] for call in broadcast.await_args_list]
    created = [message for message in messages if isinstance(message, AlertCreatedMessage)]
    updated = [message for message in messages if isinstance(message, AlertUpdatedMessage)]
    assert len(created) == 1
    assert len(updated) == 1
    persisted = (await client.get("/api/v1/alerts?rule_id=DET-SSH-001")).json()["items"][0]
    assert str(created[0].data.id) == persisted["id"]
