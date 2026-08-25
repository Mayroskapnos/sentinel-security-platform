from datetime import datetime
from ipaddress import ip_address
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import EventSeverity
from app.schemas.asset import AssetReference
from app.schemas.common import as_utc


def validate_optional_ip(value: str | None) -> str | None:
    if value is None:
        return None
    return str(ip_address(value))


class SecurityEventCreate(BaseModel):
    timestamp: datetime
    event_type: str = Field(min_length=1, max_length=64)
    source: str = Field(min_length=1, max_length=64)
    source_ip: str | None = None
    destination_ip: str | None = None
    source_port: int | None = Field(default=None, ge=0, le=65535)
    destination_port: int | None = Field(default=None, ge=0, le=65535)
    hostname: str | None = Field(default=None, max_length=255)
    username: str | None = Field(default=None, max_length=255)
    process_name: str | None = Field(default=None, max_length=255)
    action: str = Field(min_length=1, max_length=128)
    status: str = Field(min_length=1, max_length=64)
    severity: EventSeverity = EventSeverity.INFORMATIONAL
    raw_event: dict[str, Any] = Field(default_factory=dict)
    normalized_data: dict[str, Any] = Field(default_factory=dict)
    asset_id: UUID | None = None
    scenario_run_id: UUID | None = None
    scenario_id: str | None = Field(default=None, pattern=r"^SCN-[0-9]{3}$", max_length=16)

    @field_validator("source_ip", "destination_ip")
    @classmethod
    def valid_ip_address(cls, value: str | None) -> str | None:
        return validate_optional_ip(value)

    @field_validator("timestamp")
    @classmethod
    def timestamp_is_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include timezone information")
        return value


class SecurityEventResponse(BaseModel):
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
    raw_event: dict[str, Any]
    normalized_data: dict[str, Any]
    asset_id: UUID | None
    scenario_run_id: UUID | None
    scenario_id: str | None
    asset: AssetReference | None
    created_at: datetime

    @field_validator("timestamp", "created_at")
    @classmethod
    def utc_database_timestamp(cls, value: datetime) -> datetime:
        return as_utc(value)


class SecurityEventFilters(BaseModel):
    hostname: str | None = Field(default=None, max_length=255)
    asset_id: UUID | None = None
    scenario_run_id: UUID | None = None
    event_type: str | None = Field(default=None, max_length=64)
    source: str | None = Field(default=None, max_length=64)
    severity: EventSeverity | None = None
    source_ip: str | None = None
    destination_ip: str | None = None
    username: str | None = Field(default=None, max_length=255)
    status: str | None = Field(default=None, max_length=64)
    start_time: datetime | None = None
    end_time: datetime | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)

    @field_validator("source_ip", "destination_ip")
    @classmethod
    def valid_ip_address(cls, value: str | None) -> str | None:
        return validate_optional_ip(value)

    @field_validator("start_time", "end_time")
    @classmethod
    def timestamp_is_timezone_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("timestamps must include timezone information")
        return value

    @model_validator(mode="after")
    def valid_time_range(self) -> "SecurityEventFilters":
        if self.start_time and self.end_time and self.start_time > self.end_time:
            raise ValueError("start_time cannot be later than end_time")
        return self
