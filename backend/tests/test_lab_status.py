from datetime import UTC, datetime

import httpx
import pytest

from tests.factories import asset_payload, event_payload


@pytest.mark.asyncio
async def test_lab_status_is_inferred_from_recent_real_lab_telemetry(
    client: httpx.AsyncClient,
) -> None:
    asset_response = await client.post(
        "/api/v1/assets",
        json=asset_payload(
            hostname="employee-01",
            ip_address="10.10.20.10",
            environment="lab",
            network_zone="employee",
            status="unknown",
        ),
    )
    asset = asset_response.json()
    event_response = await client.post(
        "/api/v1/events",
        json=event_payload(
            timestamp=datetime.now(UTC),
            hostname="employee-01",
            source="container_health",
            event_type="service_status",
            action="heartbeat",
            status="success",
            normalized_data={"origin": "corporate_lab"},
        ),
    )
    assert event_response.status_code == 201

    response = await client.get("/api/v1/lab/status")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["collector_status"] == "active"
    employee = next(item for item in data["assets"] if item["hostname"] == "employee-01")
    assert employee["status"] == "online"
    assert employee["telemetry_status"] == "active"
    refreshed = await client.get(f"/api/v1/assets/{asset['id']}")
    assert refreshed.json()["status"] == "online"
