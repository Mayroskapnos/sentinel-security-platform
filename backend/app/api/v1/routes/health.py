import time

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.db.session import check_database
from app.schemas.health import ComponentHealth, HealthResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": HealthResponse}},
    summary="Check API and database health",
)
async def health_check() -> HealthResponse | JSONResponse:
    """Report service health after verifying the database connection."""
    started_at = time.perf_counter()
    database_healthy = await check_database()
    latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
    settings = get_settings()

    response = HealthResponse(
        status="healthy" if database_healthy else "degraded",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.sentinel_env,
        checks={
            "api": ComponentHealth(status="healthy"),
            "database": ComponentHealth(
                status="healthy" if database_healthy else "unavailable",
                latency_ms=latency_ms,
            ),
        },
    )

    if not database_healthy:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=response.model_dump(mode="json"),
        )
    return response
