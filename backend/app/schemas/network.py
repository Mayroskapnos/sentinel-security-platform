from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import AssetStatus, AssetType, Criticality
from app.schemas.common import as_utc

TopologyWindow = Literal["5m", "15m", "1h", "24h", "all"]
ActivityState = Literal["active", "recent", "historical"]


class ConnectionAssetReference(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    hostname: str
    display_name: str
    ip_address: str
    network_zone: str


class NetworkConnectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_asset_id: UUID
    destination_asset_id: UUID
    source_asset: ConnectionAssetReference
    destination_asset: ConnectionAssetReference
    source_ip: str
    destination_ip: str
    source_port: int | None
    destination_port: int | None
    protocol: str
    connection_type: str
    first_seen: datetime
    last_seen: datetime
    connection_count: int
    last_status: str
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @field_validator("first_seen", "last_seen", "created_at", "updated_at")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        return as_utc(value)


class NetworkConnectionFilters(BaseModel):
    source_asset_id: UUID | None = None
    destination_asset_id: UUID | None = None
    protocol: str | None = Field(default=None, min_length=1, max_length=32)
    destination_port: int | None = Field(default=None, ge=0, le=65535)
    start_time: datetime | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)

    @field_validator("start_time")
    @classmethod
    def timezone_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("start_time must include timezone information")
        return value


class TopologyNode(BaseModel):
    id: UUID
    hostname: str
    display_name: str
    ip_address: str
    asset_type: AssetType
    operating_system: str
    environment: str
    network_zone: str
    status: AssetStatus
    risk_score: float
    criticality: Criticality
    first_seen: datetime
    last_seen: datetime
    open_alert_count: int = Field(ge=0)
    recent_event_count: int = Field(ge=0)
    recent_connection_count: int = Field(ge=0)
    alert_ids: list[UUID] = Field(default_factory=list)

    @field_validator("first_seen", "last_seen")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        return as_utc(value)


class TopologyAlertReference(BaseModel):
    id: UUID
    title: str
    severity: str
    status: str
    rule_id: str
    timestamp: datetime

    @field_validator("timestamp")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        return as_utc(value)


class TopologyEdge(BaseModel):
    id: UUID
    source_asset_id: UUID
    destination_asset_id: UUID
    source_ip: str
    destination_ip: str
    source_port: int | None
    destination_port: int | None
    protocol: str
    connection_type: str
    first_seen: datetime
    last_seen: datetime
    connection_count: int = Field(ge=1)
    recent_event_count: int = Field(ge=1)
    last_status: str
    activity_state: ActivityState
    alert_ids: list[UUID] = Field(default_factory=list)
    scenario_run_ids: list[UUID] = Field(default_factory=list)
    event_ids: list[UUID] = Field(default_factory=list)

    @field_validator("first_seen", "last_seen")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        return as_utc(value)


class TopologyActivity(BaseModel):
    id: UUID
    timestamp: datetime
    event_type: str
    action: str
    status: str
    source_asset_id: UUID | None
    destination_asset_id: UUID | None
    source_ip: str | None
    destination_ip: str | None
    destination_port: int | None
    scenario_run_id: UUID | None

    @field_validator("timestamp")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        return as_utc(value)


class ObservedTechnique(BaseModel):
    technique_id: str
    technique_name: str
    tactic: str
    alert_ids: list[UUID]


class TopologyScenarioContext(BaseModel):
    run_id: UUID
    scenario_id: str
    scenario_name: str
    status: str
    event_count: int = Field(ge=0)
    alert_count: int = Field(ge=0)
    started_at: datetime | None
    finished_at: datetime | None

    @field_validator("started_at", "finished_at")
    @classmethod
    def utc_timestamp(cls, value: datetime | None) -> datetime | None:
        return as_utc(value) if value else None


class TopologySummary(BaseModel):
    asset_count: int = Field(ge=0)
    connection_count: int = Field(ge=0)
    active_connection_count: int = Field(ge=0)
    open_alert_count: int = Field(ge=0)
    high_risk_asset_count: int = Field(ge=0)
    activity_count: int = Field(ge=0)
    activity_truncated: bool = False


class NetworkTopologyResponse(BaseModel):
    generated_at: datetime
    window: TopologyWindow
    scenario: TopologyScenarioContext | None = None
    nodes: list[TopologyNode]
    edges: list[TopologyEdge]
    alerts: list[TopologyAlertReference]
    activities: list[TopologyActivity]
    observed_techniques: list[ObservedTechnique]
    summary: TopologySummary

    @field_validator("generated_at")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        return as_utc(value)


class NetworkConnectionUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_asset_id: UUID
    destination_asset_id: UUID
    destination_port: int | None
    protocol: str
    connection_type: str
    last_seen: datetime
    connection_count: int
    last_status: str

    @field_validator("last_seen")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        return as_utc(value)
