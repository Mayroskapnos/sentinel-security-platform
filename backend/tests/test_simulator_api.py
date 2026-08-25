import httpx
import pytest


@pytest.mark.asyncio
async def test_scenario_metadata_is_readable_when_execution_is_disabled(
    client: httpx.AsyncClient,
) -> None:
    response = await client.get("/api/v1/simulator/scenarios")
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [
        "SCN-001",
        "SCN-002",
        "SCN-003",
        "SCN-004",
        "SCN-005",
    ]

    detail = await client.get("/api/v1/simulator/scenarios/SCN-004")
    assert detail.status_code == 200
    assert detail.json()["expected_detections"] == ["DET-DB-001"]
    assert "mitre" not in detail.json()


@pytest.mark.asyncio
async def test_disabled_simulator_rejects_execution_without_a_request_body(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post("/api/v1/simulator/run/SCN-001")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SIMULATOR_DISABLED"


@pytest.mark.asyncio
async def test_unknown_scenario_returns_structured_not_found(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/simulator/scenarios/SCN-999")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SCENARIO_NOT_FOUND"
