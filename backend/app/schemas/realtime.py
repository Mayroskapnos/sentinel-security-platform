from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

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


class SimulationRunData(BaseModel):
    run_id: UUID
    scenario_id: str
    status: str
    current_step: int
    total_steps: int
    label: str | None = None
    message: str | None = None


class _SimulationMessage(BaseModel):
    version: Literal["1"] = "1"
    timestamp: datetime = Field(default_factory=utc_now)
    data: SimulationRunData

    @classmethod
    def from_run(cls, run: Any, step: dict[str, Any] | None = None):  # noqa: ANN206
        return cls(
            data=SimulationRunData(
                run_id=run.id,
                scenario_id=run.scenario_id,
                status=(step or {}).get("status", run.status),
                current_step=run.current_step,
                total_steps=run.total_steps,
                label=(step or {}).get("name"),
                message=(step or {}).get("message", run.error_message),
            )
        )


class SimulationStartedMessage(_SimulationMessage):
    type: Literal["simulation_started"] = "simulation_started"


class SimulationStepMessage(_SimulationMessage):
    type: Literal["simulation_step"] = "simulation_step"


class SimulationFinishedMessage(_SimulationMessage):
    type: Literal["simulation_finished"] = "simulation_finished"


class SimulationFailedMessage(_SimulationMessage):
    type: Literal["simulation_failed"] = "simulation_failed"


class SimulationCancelledMessage(_SimulationMessage):
    type: Literal["simulation_cancelled"] = "simulation_cancelled"
