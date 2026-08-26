from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import AlertStatus, EventSeverity
from app.schemas.asset import AssetReference
from app.schemas.common import as_utc
from app.schemas.incident import IncidentReference


class AlertRuleReference(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    rule_id: str
    name: str


class EvidenceEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    timestamp: datetime
    event_type: str
    source: str
    source_ip: str | None
    destination_ip: str | None
    source_port: int | None
    destination_port: int | None
    hostname: str | None
    username: str | None
    process_name: str | None
    action: str
    status: str
    severity: EventSeverity
    asset_id: UUID | None

    @field_validator("timestamp")
    @classmethod
    def utc_database_timestamp(cls, value: datetime) -> datetime:
        return as_utc(value)


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    timestamp: datetime
    title: str
    description: str
    severity: EventSeverity
    status: AlertStatus
    detection_rule_id: UUID
    detection_rule: AlertRuleReference
    asset_id: UUID | None
    asset: AssetReference | None
    source_ip: str | None
    destination_ip: str | None
    username: str | None
    risk_score: float
    mitre_tactic: str | None
    mitre_technique_id: str | None
    mitre_technique_name: str | None
    evidence: dict[str, Any]
    metadata_json: dict[str, Any]
    evidence_count: int
    first_event_at: datetime
    last_event_at: datetime
    created_at: datetime
    updated_at: datetime
    incident: IncidentReference | None = None

    @field_validator("timestamp", "first_event_at", "last_event_at", "created_at", "updated_at")
    @classmethod
    def utc_database_timestamp(cls, value: datetime) -> datetime:
        return as_utc(value)


class AlertDetailResponse(AlertResponse):
    evidence_events: list[EvidenceEventResponse]


class AlertFilters(BaseModel):
    severity: EventSeverity | None = None
    status: AlertStatus | None = None
    rule_id: str | None = Field(default=None, max_length=64)
    asset_id: UUID | None = None
    source_ip: str | None = Field(default=None, max_length=45)
    destination_ip: str | None = Field(default=None, max_length=45)
    username: str | None = Field(default=None, max_length=255)
    active_only: bool = False
    start_time: datetime | None = None
    end_time: datetime | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)


class AlertUpdate(BaseModel):
    status: AlertStatus
