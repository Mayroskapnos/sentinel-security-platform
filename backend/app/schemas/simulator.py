from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import ScenarioRunStatus, ScenarioStepStatus
from app.schemas.common import as_utc
from app.schemas.incident import IncidentReference
from app.simulator.registry import LabTargetRegistry

ActionName = Literal[
    "controlled_failed_authentication",
    "controlled_successful_authentication",
    "internal_service_discovery",
    "controlled_privileged_activity",
    "controlled_database_connection",
    "wait",
]


class ScenarioStepDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    action: ActionName
    target: str | None = Field(default=None, max_length=32)
    count: int | None = Field(default=None, ge=1, le=15)
    seconds: int | None = Field(default=None, ge=1, le=10)

    @model_validator(mode="after")
    def validate_action_shape(self) -> "ScenarioStepDefinition":
        if self.action == "wait":
            if self.target is not None or self.count is not None or self.seconds is None:
                raise ValueError("wait requires only a bounded seconds field")
            return self

        if self.target is None or not LabTargetRegistry.contains(self.target):
            raise ValueError("action target must be a registered Corporate Lab asset")
        if self.seconds is not None:
            raise ValueError("seconds is supported only by wait")
        if self.action == "controlled_failed_authentication":
            if self.target != "employee-01" or self.count is None:
                raise ValueError("failed authentication is fixed to employee-01 with a count")
        elif self.count is not None:
            raise ValueError("count is supported only by controlled failed authentication")

        allowed_targets = {
            "controlled_successful_authentication": "employee-01",
            "internal_service_discovery": "employee-01",
            "controlled_privileged_activity": "admin-server",
            "controlled_database_connection": "employee-01",
        }
        expected_target = allowed_targets.get(self.action)
        if expected_target is not None and self.target != expected_target:
            raise ValueError(f"{self.action} is fixed to {expected_target}")
        return self


class ScenarioDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^SCN-[0-9]{3}$", max_length=16)
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=1000)
    risk: Literal["low"]
    estimated_seconds: int = Field(ge=1, le=180)
    targets: list[str] = Field(min_length=1, max_length=5)
    expected_detections: list[str] = Field(min_length=1, max_length=5)
    steps: list[ScenarioStepDefinition] = Field(min_length=1, max_length=12)

    @field_validator("targets")
    @classmethod
    def valid_targets(cls, targets: list[str]) -> list[str]:
        if len(targets) != len(set(targets)):
            raise ValueError("scenario targets must be unique")
        invalid = sorted(set(targets) - LabTargetRegistry.ids())
        if invalid:
            raise ValueError("scenario targets must use the Corporate Lab target registry")
        return targets

    @field_validator("expected_detections")
    @classmethod
    def valid_detection_ids(cls, detections: list[str]) -> list[str]:
        if len(detections) != len(set(detections)):
            raise ValueError("expected detections must be unique")
        if any(not item.startswith("DET-") or len(item) > 64 for item in detections):
            raise ValueError("expected detections must use rule IDs")
        return detections

    @model_validator(mode="after")
    def enforce_safety_limits(self) -> "ScenarioDefinition":
        step_targets = {step.target for step in self.steps if step.target is not None}
        if not step_targets.issubset(set(self.targets)):
            raise ValueError("every step target must be declared by the scenario")
        connection_actions = sum(
            step.action in {"internal_service_discovery", "controlled_database_connection"}
            for step in self.steps
        )
        if connection_actions > 3:
            raise ValueError("scenario exceeds the internal connection action limit")
        total_wait = sum(step.seconds or 0 for step in self.steps)
        if total_wait > 30:
            raise ValueError("scenario exceeds the cumulative wait limit")
        return self


class ScenarioSummary(BaseModel):
    id: str
    name: str
    description: str
    risk: Literal["low"]
    estimated_seconds: int
    targets: list[str]
    expected_detections: list[str]
    step_count: int


class ScenarioDetail(ScenarioSummary):
    steps: list[ScenarioStepDefinition]


class ScenarioRunStep(BaseModel):
    index: int = Field(ge=1)
    name: str
    action: ActionName
    status: ScenarioStepStatus
    started_at: datetime | None = None
    finished_at: datetime | None = None
    message: str | None = None

    @field_validator("started_at", "finished_at")
    @classmethod
    def utc_timestamp(cls, value: datetime | None) -> datetime | None:
        return as_utc(value) if value else None


class DetectionObservation(BaseModel):
    rule_id: str
    observed: bool
    alert_ids: list[UUID] = Field(default_factory=list)
    note: str | None = None


class ScenarioAlertReference(BaseModel):
    id: UUID
    rule_id: str
    title: str
    severity: str
    timestamp: datetime

    @field_validator("timestamp")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        return as_utc(value)


class ScenarioRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    scenario_id: str
    scenario_name: str
    status: ScenarioRunStatus
    started_at: datetime | None
    finished_at: datetime | None
    current_step: int
    total_steps: int
    requested_by: str
    steps: list[ScenarioRunStep]
    expected_detections: list[str]
    targets: list[str]
    result: dict[str, Any]
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    event_count: int = 0
    alert_count: int = 0
    detections: list[DetectionObservation] = Field(default_factory=list)
    alerts: list[ScenarioAlertReference] = Field(default_factory=list)
    incident: IncidentReference | None = None

    @field_validator("started_at", "finished_at", "created_at", "updated_at")
    @classmethod
    def utc_timestamp(cls, value: datetime | None) -> datetime | None:
        return as_utc(value) if value else None


class ScenarioRunPage(BaseModel):
    items: list[ScenarioRunResponse]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total: int = Field(ge=0)
    pages: int = Field(ge=0)


class SimulatorStatusResponse(BaseModel):
    enabled: bool
    available: bool
    state: Literal["disabled", "unavailable", "idle", "running"]
    active_run: ScenarioRunResponse | None = None
    message: str
