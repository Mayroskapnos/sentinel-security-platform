from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.enums import ScenarioRunStatus
from app.models.scenario_run import ScenarioRun
from tests.factories import asset_payload, event_payload


@pytest.mark.asyncio
async def test_unknown_scenario_attribution_is_rejected_without_losing_event(
    client: httpx.AsyncClient,
) -> None:
    payload = event_payload(
        scenario_run_id="cc6957e0-b1dd-4ca3-85b0-7106ee63b466",
        scenario_id="SCN-001",
    )

    response = await client.post("/api/v1/events", json=payload)

    assert response.status_code == 201
    document = response.json()
    assert document["scenario_run_id"] is None
    assert document["scenario_id"] is None
    assert document["normalized_data"]["scenario_attribution_rejected"] is True


@pytest.mark.asyncio
async def test_valid_scenario_attribution_is_persisted_by_the_backend(
    client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        run = ScenarioRun(
            scenario_id="SCN-004",
            scenario_name="Unexpected Workstation Database Access",
            status=ScenarioRunStatus.COMPLETED,
            current_step=1,
            total_steps=1,
            steps=[],
            expected_detections=["DET-DB-001"],
            targets=["employee-01", "database"],
            result={},
        )
        session.add(run)
        await session.commit()
        run_id = run.id

    response = await client.post(
        "/api/v1/events",
        json=event_payload(scenario_run_id=str(run_id), scenario_id="SCN-004"),
    )

    assert response.status_code == 201
    document = response.json()
    assert document["scenario_run_id"] == str(run_id)
    assert document["scenario_id"] == "SCN-004"
    assert document["normalized_data"]["scenario_run_id"] == str(run_id)


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
            source="linux_process",
            severity="informational",
            status="success",
            source_ip=None,
            destination_ip=None,
        ),
    )

    response = await client.get(
        "/api/v1/events",
        params={
            "event_type": "authentication",
            "source": "linux_auth",
            "severity": "medium",
            "status": "failed",
        },
    )
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["event_type"] == "authentication"
    assert response.json()["items"][0]["source"] == "linux_auth"


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
