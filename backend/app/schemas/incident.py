from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import AlertStatus, EventSeverity, IncidentStatus
from app.schemas.common import as_utc

CorrelationStrength = Literal["foundational", "strong", "moderate", "supporting"]


class IncidentReference(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    incident_number: str
    title: str
    severity: EventSeverity
    status: IncidentStatus


class CorrelationSignal(BaseModel):
    type: str
    weight: int = Field(ge=0, le=100)
    strength: CorrelationStrength
    description: str
    details: dict[str, Any] = Field(default_factory=dict)


class IncidentAssetReference(BaseModel):
    id: UUID
    hostname: str
    display_name: str
    ip_address: str
    asset_type: str
    network_zone: str
    criticality: str
    status: str
    risk_score: float


class IncidentAlertReference(BaseModel):
    id: UUID
    rule_id: str
    title: str
    severity: EventSeverity
    status: AlertStatus
    timestamp: datetime
    first_event_at: datetime
    last_event_at: datetime
    asset_id: UUID | None
    asset_hostname: str | None
    evidence_count: int = Field(ge=0)
    correlation_score: int = Field(ge=0, le=100)
    correlation_reasons: list[CorrelationSignal]

    @field_validator("timestamp", "first_event_at", "last_event_at")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        return as_utc(value)


class IncidentStoryItem(BaseModel):
    timestamp: datetime
    stage: str
    title: str
    description: str
    alert_id: UUID
    rule_id: str
    asset_ids: list[UUID] = Field(default_factory=list)
    event_ids: list[UUID] = Field(default_factory=list)
    source_ip: str | None = None
    destination_ip: str | None = None
    mitre_technique_id: str | None = None
    mitre_technique_name: str | None = None
    network_connection_id: UUID | None = None
    scenario_step: str | None = None

    @field_validator("timestamp")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        return as_utc(value)


class IncidentTechnique(BaseModel):
    technique_id: str
    technique_name: str
    tactic: str
    first_observed_at: datetime
    alert_ids: list[UUID]

    @field_validator("first_observed_at")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        return as_utc(value)


class IncidentScenarioReference(BaseModel):
    id: UUID
    scenario_id: str
    scenario_name: str
    status: str


class IncidentListItem(IncidentReference):
    confidence_score: int = Field(ge=0, le=100)
    risk_score: float = Field(ge=0, le=100)
    first_activity_at: datetime
    last_activity_at: datetime
    created_at: datetime
    updated_at: datetime
    alert_count: int = Field(ge=0)
    asset_count: int = Field(ge=0)
    event_count: int = Field(ge=0)
    affected_assets: list[str] = Field(default_factory=list)
    scenario_run_id: UUID | None = None

    @field_validator("first_activity_at", "last_activity_at", "created_at", "updated_at")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        return as_utc(value)


class IncidentDetail(IncidentListItem):
    description: str
    summary: str
    closed_at: datetime | None
    assigned_to: str | None
    correlation_signals: list[CorrelationSignal]
    story: list[IncidentStoryItem]
    alerts: list[IncidentAlertReference]
    assets: list[IncidentAssetReference]
    observed_techniques: list[IncidentTechnique]
    scenario: IncidentScenarioReference | None
    metadata_json: dict[str, Any]

    @field_validator("closed_at")
    @classmethod
    def utc_optional_timestamp(cls, value: datetime | None) -> datetime | None:
        return as_utc(value) if value else None


class IncidentFilters(BaseModel):
    severity: EventSeverity | None = None
    status: IncidentStatus | None = None
    asset_id: UUID | None = None
    scenario_run_id: UUID | None = None
    confidence_min: int | None = Field(default=None, ge=0, le=100)
    start_time: datetime | None = None
    end_time: datetime | None = None
    search: str | None = Field(default=None, max_length=255)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)

    @field_validator("start_time", "end_time")
    @classmethod
    def timezone_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("incident time filters must include timezone information")
        return value


class IncidentUpdate(BaseModel):
    status: IncidentStatus | None = None
    assigned_to: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def at_least_one_change(self) -> "IncidentUpdate":
        if "status" not in self.model_fields_set and "assigned_to" not in self.model_fields_set:
            raise ValueError("at least one incident field must be provided")
        return self


class IncidentCorrelationResult(BaseModel):
    incident: IncidentListItem
    created: bool
