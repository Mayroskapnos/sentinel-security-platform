from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.alert import AlertResponse
from app.schemas.security_event import SecurityEventResponse


def utc_now() -> datetime:
    return datetime.now(UTC)


class SecurityEventMessage(BaseModel):
    version: Literal["1"] = "1"
    type: Literal["security_event"] = "security_event"
    timestamp: datetime = Field(default_factory=utc_now)
    data: SecurityEventResponse


class TelemetryStatusData(BaseModel):
    status: Literal["connected"] = "connected"
    connected_clients: int = Field(ge=1)


class TelemetryStatusMessage(BaseModel):
    version: Literal["1"] = "1"
    type: Literal["telemetry_status"] = "telemetry_status"
    timestamp: datetime = Field(default_factory=utc_now)
    data: TelemetryStatusData


class AlertCreatedMessage(BaseModel):
    version: Literal["1"] = "1"
    type: Literal["alert_created"] = "alert_created"
    timestamp: datetime = Field(default_factory=utc_now)
    data: AlertResponse


class AlertUpdatedMessage(BaseModel):
    version: Literal["1"] = "1"
    type: Literal["alert_updated"] = "alert_updated"
    timestamp: datetime = Field(default_factory=utc_now)
    data: AlertResponse
