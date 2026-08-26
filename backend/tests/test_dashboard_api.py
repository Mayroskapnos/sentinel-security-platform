from datetime import UTC, datetime

import httpx
import pytest

from tests.factories import asset_payload, event_payload


@pytest.mark.asyncio
async def test_dashboard_summary_uses_database_counts(client: httpx.AsyncClient) -> None:
    asset = (
        await client.post("/api/v1/assets", json=asset_payload(risk_score=75, status="online"))
    ).json()
    await client.post(
        "/api/v1/events", json=event_payload(timestamp=datetime.now(UTC), asset_id=asset["id"])
    )

    response = await client.get("/api/v1/dashboard/summary")
    assert response.status_code == 200
    assert response.json() == {
        "total_assets": 1,
        "online_assets": 1,
        "high_risk_assets": 1,
        "events_today": 1,
        "events_last_hour": 1,
        "open_alerts": 0,
        "critical_alerts": 0,
        "high_alerts": 0,
        "open_incidents": 0,
        "critical_incidents": 0,
    }


@pytest.mark.asyncio
async def test_dashboard_activity_aggregates_events(client: httpx.AsyncClient) -> None:
    asset = (await client.post("/api/v1/assets", json=asset_payload())).json()
    await client.post(
        "/api/v1/events",
        json=event_payload(timestamp=datetime.now(UTC), asset_id=asset["id"]),
    )
    await client.post(
        "/api/v1/events",
        json=event_payload(
            timestamp=datetime.now(UTC), asset_id=asset["id"], event_type="network_connection"
        ),
    )

    response = await client.get("/api/v1/dashboard/activity", params={"hours": 24})
    assert response.status_code == 200
    assert sum(bucket["count"] for bucket in response.json()["events_over_time"]) == 2
    assert response.json()["most_active_assets"][0]["count"] == 2
    assert {bucket["name"] for bucket in response.json()["events_by_type"]} == {
        "authentication",
        "network_connection",
    }
