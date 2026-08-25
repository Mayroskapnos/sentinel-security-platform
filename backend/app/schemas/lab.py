from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class LabAssetStatus(BaseModel):
    hostname: str
    display_name: str
    network_zone: str
    status: Literal["online", "offline"]
    telemetry_status: Literal["active", "stale"]
    last_telemetry: datetime | None


class LabSourceStatus(BaseModel):
    source: str
    status: Literal["active", "stale"]
    last_telemetry: datetime | None


class LabStatusResponse(BaseModel):
    version: str
    status: Literal["running", "degraded", "offline"]
    collector_status: Literal["active", "stale"]
    active_assets: int
    total_assets: int
    assets: list[LabAssetStatus]
    sources: list[LabSourceStatus]
