import httpx
import pytest

from app.api.v1.routes import health
from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint_reports_database_connectivity(monkeypatch) -> None:
    async def database_is_healthy() -> bool:
        return True

    monkeypatch.setattr(health, "check_database", database_is_healthy)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["checks"]["api"]["status"] == "healthy"
    assert payload["checks"]["database"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_endpoint_reports_degraded_state(monkeypatch) -> None:
    async def database_is_unavailable() -> bool:
        return False

    monkeypatch.setattr(health, "check_database", database_is_unavailable)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
    assert response.json()["checks"]["database"]["status"] == "unavailable"
