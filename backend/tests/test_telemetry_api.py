from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import httpx
import pytest

from app.core.config import get_settings
from app.realtime.manager import websocket_manager
from app.schemas.realtime import SecurityEventMessage
from app.services.events import SecurityEventService
from app.services.telemetry import TelemetryIngestionService
from tests.factories import asset_payload, event_payload


async def create_asset(
    client: httpx.AsyncClient,
    hostname: str = "test-host",
    ip_address: str = "10.10.20.50",
    **overrides,
) -> dict:
    response = await client.post(
        "/api/v1/assets",
        json=asset_payload(hostname=hostname, ip_address=ip_address, **overrides),
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_valid_telemetry_is_persisted_and_broadcast_with_database_id(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    asset = await create_asset(client)
    broadcast = AsyncMock()
    monkeypatch.setattr(websocket_manager, "broadcast", broadcast)

    response = await client.post("/api/v1/telemetry/events", json=event_payload())

    assert response.status_code == 201
    event = response.json()
    assert event["id"]
    assert event["asset_id"] == asset["id"]
    detail = await client.get(f"/api/v1/events/{event['id']}")
    assert detail.status_code == 200
    message = broadcast.await_args.args[0]
    assert isinstance(message, SecurityEventMessage)
    assert str(message.data.id) == event["id"]


@pytest.mark.asyncio
async def test_telemetry_resolves_asset_by_destination_ip(client: httpx.AsyncClient) -> None:
    asset = await create_asset(client)
    payload = event_payload(hostname="unknown-host")

    response = await client.post("/api/v1/telemetry/events", json=payload)

    assert response.status_code == 201
    assert response.json()["asset_id"] == asset["id"]
    assert response.json()["hostname"] == "unknown-host"


@pytest.mark.asyncio
async def test_telemetry_resolves_asset_by_source_ip(client: httpx.AsyncClient) -> None:
    asset = await create_asset(client, ip_address="10.10.50.2")
    payload = event_payload(
        hostname=None,
        source_ip="10.10.50.2",
        destination_ip="192.0.2.10",
    )

    response = await client.post("/api/v1/telemetry/events", json=payload)

    assert response.status_code == 201
    assert response.json()["asset_id"] == asset["id"]
    assert response.json()["hostname"] == asset["hostname"]


@pytest.mark.asyncio
async def test_ambiguous_ip_resolution_leaves_event_unresolved(client: httpx.AsyncClient) -> None:
    await create_asset(client, hostname="source-host", ip_address="10.10.50.2")
    await create_asset(
        client,
        hostname="destination-host",
        ip_address="10.10.20.50",
        mac_address="02:42:0a:0a:14:33",
    )

    response = await client.post(
        "/api/v1/telemetry/events",
        json=event_payload(hostname=None),
    )

    assert response.status_code == 201
    assert response.json()["asset_id"] is None


@pytest.mark.asyncio
async def test_unknown_asset_is_allowed(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/v1/telemetry/events",
        json=event_payload(
            hostname="not-in-inventory",
            source_ip="192.0.2.5",
            destination_ip="198.51.100.8",
        ),
    )

    assert response.status_code == 201
    assert response.json()["asset_id"] is None


@pytest.mark.asyncio
async def test_telemetry_normalizes_timestamp_to_utc(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/v1/telemetry/events",
        json=event_payload(timestamp="2026-08-24T16:22:17+02:00"),
    )

    assert response.status_code == 201
    timestamp = datetime.fromisoformat(response.json()["timestamp"])
    assert timestamp == datetime(2026, 8, 24, 14, 22, 17, tzinfo=UTC)


@pytest.mark.asyncio
async def test_asset_last_seen_only_moves_forward(client: httpx.AsyncClient) -> None:
    asset = await create_asset(client)
    newer = datetime(2026, 8, 24, 12, tzinfo=UTC)
    older = newer - timedelta(hours=4)

    first = await client.post(
        "/api/v1/telemetry/events",
        json=event_payload(timestamp=newer, asset_id=asset["id"]),
    )
    second = await client.post(
        "/api/v1/telemetry/events",
        json=event_payload(timestamp=older, asset_id=asset["id"]),
    )

    assert first.status_code == 201
    assert second.status_code == 201
    refreshed = await client.get(f"/api/v1/assets/{asset['id']}")
    assert datetime.fromisoformat(refreshed.json()["last_seen"]) == newer


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "overrides",
    [
        {"source_ip": "999.10.10.10"},
        {"severity": "emergency"},
        {"timestamp": "2026-08-24T14:22:17"},
        {"event_type": ""},
    ],
)
async def test_malformed_telemetry_is_rejected(client: httpx.AsyncClient, overrides: dict) -> None:
    response = await client.post(
        "/api/v1/telemetry/events",
        json=event_payload(**overrides),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_oversized_telemetry_is_rejected(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/v1/telemetry/events",
        headers={"Content-Length": "262145"},
        json=event_payload(),
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "TELEMETRY_PAYLOAD_TOO_LARGE"


@pytest.mark.asyncio
async def test_configured_collector_key_protects_ingestion(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "collector_api_key", "test-collector-key-1234")

    missing = await client.post("/api/v1/telemetry/events", json=event_payload())
    invalid = await client.post(
        "/api/v1/telemetry/events",
        headers={"X-Sentinel-Collector-Key": "wrong-key"},
        json=event_payload(),
    )
    accepted = await client.post(
        "/api/v1/telemetry/events",
        headers={"X-Sentinel-Collector-Key": "test-collector-key-1234"},
        json=event_payload(),
    )

    assert missing.status_code == invalid.status_code == 401
    assert missing.json()["error"]["code"] == "COLLECTOR_AUTHENTICATION_FAILED"
    assert accepted.status_code == 201


@pytest.mark.asyncio
async def test_persistence_failure_does_not_broadcast(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    create = AsyncMock(side_effect=RuntimeError("database unavailable"))
    broadcast = AsyncMock()
    monkeypatch.setattr(SecurityEventService, "create", create)
    monkeypatch.setattr(websocket_manager, "broadcast", broadcast)
    service = TelemetryIngestionService(AsyncMock())

    with pytest.raises(RuntimeError, match="database unavailable"):
        await service.ingest(event_payload())
    broadcast.assert_not_awaited()
