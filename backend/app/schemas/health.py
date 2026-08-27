from typing import Literal

from pydantic import BaseModel, Field


class ComponentHealth(BaseModel):
    status: Literal["healthy", "unavailable"]
    latency_ms: float | None = Field(default=None, ge=0)


class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded"]
    service: str
    version: str
    build_sha: str | None = None
    build_time: str | None = None
    environment: str
    checks: dict[str, ComponentHealth]
