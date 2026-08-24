from uuid import uuid4

import httpx
import pytest

from tests.factories import asset_payload


@pytest.mark.asyncio
async def test_create_and_retrieve_asset(client: httpx.AsyncClient) -> None:
    created = await client.post("/api/v1/assets", json=asset_payload())
    assert created.status_code == 201
    asset_id = created.json()["id"]

    response = await client.get(f"/api/v1/assets/{asset_id}")
    assert response.status_code == 200
    assert response.json()["hostname"] == "test-host"
    assert response.json()["metadata_json"] == {"test": True}


@pytest.mark.asyncio
async def test_update_asset(client: httpx.AsyncClient) -> None:
    created = await client.post("/api/v1/assets", json=asset_payload())
    response = await client.patch(
        f"/api/v1/assets/{created.json()['id']}",
        json={"status": "warning", "risk_score": 72},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "warning"
    assert response.json()["risk_score"] == 72


@pytest.mark.asyncio
async def test_list_filter_and_search_assets(client: httpx.AsyncClient) -> None:
    await client.post("/api/v1/assets", json=asset_payload())
    await client.post(
        "/api/v1/assets",
        json=asset_payload(
            hostname="database-test",
            ip_address="10.10.30.50",
            asset_type="database",
            network_zone="server",
            risk_score=80,
        ),
    )

    response = await client.get(
        "/api/v1/assets", params={"asset_type": "database", "min_risk_score": 60}
    )
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["hostname"] == "database-test"

    search = await client.get("/api/v1/assets", params={"search": "10.10.20.50"})
    assert search.json()["items"][0]["hostname"] == "test-host"


@pytest.mark.asyncio
async def test_asset_pagination(client: httpx.AsyncClient) -> None:
    for index in range(5):
        await client.post(
            "/api/v1/assets",
            json=asset_payload(
                hostname=f"host-{index}",
                ip_address=f"10.10.20.{index + 50}",
                mac_address=f"02:42:0a:0a:14:{index + 10:02x}",
            ),
        )

    response = await client.get("/api/v1/assets", params={"page": 2, "page_size": 2})
    assert response.status_code == 200
    assert len(response.json()["items"]) == 2
    assert response.json()["total"] == 5
    assert response.json()["pages"] == 3


@pytest.mark.asyncio
async def test_asset_not_found_uses_structured_error(client: httpx.AsyncClient) -> None:
    response = await client.get(f"/api/v1/assets/{uuid4()}")
    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "ASSET_NOT_FOUND", "message": "Requested asset does not exist."}
    }


@pytest.mark.asyncio
async def test_asset_validation_rejects_bad_risk_and_ip(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/v1/assets", json=asset_payload(ip_address="not-an-ip", risk_score=101)
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_asset_validation_requires_aware_timestamps_and_non_null_patch(
    client: httpx.AsyncClient,
) -> None:
    invalid_timestamp = await client.post(
        "/api/v1/assets", json=asset_payload(first_seen="2026-08-20T10:00:00")
    )
    assert invalid_timestamp.status_code == 422

    created = await client.post("/api/v1/assets", json=asset_payload())
    invalid_patch = await client.patch(
        f"/api/v1/assets/{created.json()['id']}", json={"operating_system": None}
    )
    assert invalid_patch.status_code == 422
