from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest

from tests.factories import asset_payload, event_payload


async def create_asset(client: httpx.AsyncClient) -> dict:
    response = await client.post("/api/v1/assets", json=asset_payload())
    return response.json()


@pytest.mark.asyncio
async def test_create_and_retrieve_resolved_event(client: httpx.AsyncClient) -> None:
    asset = await create_asset(client)
    response = await client.post("/api/v1/events", json=event_payload(asset_id=asset["id"]))
    assert response.status_code == 201
    assert response.json()["asset"]["hostname"] == "test-host"

    detail = await client.get(f"/api/v1/events/{response.json()['id']}")
    assert detail.status_code == 200
    assert detail.json()["normalized_data"] == {"service": "ssh"}


@pytest.mark.asyncio
async def test_event_automatically_resolves_asset_by_hostname(client: httpx.AsyncClient) -> None:
    asset = await create_asset(client)
    response = await client.post("/api/v1/events", json=event_payload())
    assert response.status_code == 201
    assert response.json()["asset_id"] == asset["id"]


@pytest.mark.asyncio
async def test_event_filters(client: httpx.AsyncClient) -> None:
    await create_asset(client)
    await client.post("/api/v1/events", json=event_payload())
    await client.post(
        "/api/v1/events",
        json=event_payload(
            event_type="process_execution",
            severity="informational",
            status="success",
            source_ip=None,
            destination_ip=None,
        ),
    )

    response = await client.get(
        "/api/v1/events",
        params={"event_type": "authentication", "severity": "medium", "status": "failed"},
    )
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["event_type"] == "authentication"


@pytest.mark.asyncio
async def test_events_are_newest_first(client: httpx.AsyncClient) -> None:
    await create_asset(client)
    now = datetime.now(UTC)
    await client.post("/api/v1/events", json=event_payload(timestamp=now - timedelta(hours=2)))
    await client.post("/api/v1/events", json=event_payload(timestamp=now, status="success"))

    response = await client.get("/api/v1/events")
    timestamps = [item["timestamp"] for item in response.json()["items"]]
    assert timestamps == sorted(timestamps, reverse=True)


@pytest.mark.asyncio
async def test_event_pagination(client: httpx.AsyncClient) -> None:
    await create_asset(client)
    for index in range(5):
        await client.post(
            "/api/v1/events",
            json=event_payload(timestamp=datetime.now(UTC) - timedelta(minutes=index)),
        )

    response = await client.get("/api/v1/events", params={"page": 2, "page_size": 2})
    assert response.status_code == 200
    assert response.json()["total"] == 5
    assert len(response.json()["items"]) == 2


@pytest.mark.asyncio
async def test_event_validation_and_missing_asset(client: httpx.AsyncClient) -> None:
    invalid = await client.post(
        "/api/v1/events", json=event_payload(destination_port=70000, timestamp="2026-08-24")
    )
    assert invalid.status_code == 422

    missing_asset = await client.post("/api/v1/events", json=event_payload(asset_id=str(uuid4())))
    assert missing_asset.status_code == 404
    assert missing_asset.json()["error"]["code"] == "ASSET_NOT_FOUND"
