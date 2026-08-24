import re
from datetime import UTC, datetime
from ipaddress import ip_address
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import AssetStatus, AssetType, Criticality

MAC_ADDRESS_PATTERN = re.compile(r"^(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")


def utc_now() -> datetime:
    return datetime.now(UTC)


def validate_ip(value: str | None) -> str | None:
    if value is None:
        return None
    return str(ip_address(value))


class AssetCreate(BaseModel):
    hostname: str = Field(min_length=1, max_length=255, pattern=r"^[A-Za-z0-9][A-Za-z0-9.-]*$")
    display_name: str = Field(min_length=1, max_length=255)
    ip_address: str
    mac_address: str | None = None
    asset_type: AssetType = AssetType.UNKNOWN
    operating_system: str = Field(min_length=1, max_length=255)
    environment: str = Field(default="development", min_length=1, max_length=64)
    network_zone: str = Field(min_length=1, max_length=64)
    status: AssetStatus = AssetStatus.UNKNOWN
    risk_score: float = Field(default=0, ge=0, le=100)
    criticality: Criticality = Criticality.MEDIUM
    first_seen: datetime = Field(default_factory=utc_now)
    last_seen: datetime = Field(default_factory=utc_now)
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("hostname")
    @classmethod
    def normalized_hostname(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("ip_address")
    @classmethod
    def valid_ip_address(cls, value: str) -> str:
        validated = validate_ip(value)
        assert validated is not None
        return validated

    @field_validator("mac_address")
    @classmethod
    def valid_mac_address(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not MAC_ADDRESS_PATTERN.fullmatch(value):
            raise ValueError("MAC address must use six colon-separated octets")
        return value.lower()

    @field_validator("first_seen", "last_seen")
    @classmethod
    def timezone_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("asset timestamps must include timezone information")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def last_seen_not_before_first_seen(self) -> "AssetCreate":
        if self.last_seen < self.first_seen:
            raise ValueError("last_seen cannot be earlier than first_seen")
        return self


class AssetUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    ip_address: str | None = None
    mac_address: str | None = None
    asset_type: AssetType | None = None
    operating_system: str | None = Field(default=None, min_length=1, max_length=255)
    environment: str | None = Field(default=None, min_length=1, max_length=64)
    network_zone: str | None = Field(default=None, min_length=1, max_length=64)
    status: AssetStatus | None = None
    risk_score: float | None = Field(default=None, ge=0, le=100)
    criticality: Criticality | None = None
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    metadata_json: dict[str, Any] | None = None

    @field_validator("ip_address")
    @classmethod
    def valid_ip_address(cls, value: str | None) -> str | None:
        return validate_ip(value)

    @field_validator("mac_address")
    @classmethod
    def valid_mac_address(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not MAC_ADDRESS_PATTERN.fullmatch(value):
            raise ValueError("MAC address must use six colon-separated octets")
        return value.lower()

    @field_validator("first_seen", "last_seen")
    @classmethod
    def timezone_aware_timestamp(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("asset timestamps must include timezone information")
        return value.astimezone(UTC) if value else None

    @model_validator(mode="after")
    def non_nullable_fields_cannot_be_cleared(self) -> "AssetUpdate":
        nullable_fields = {"mac_address"}
        for field_name in self.model_fields_set - nullable_fields:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class AssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    hostname: str
    display_name: str
    ip_address: str
    mac_address: str | None
    asset_type: AssetType
    operating_system: str
    environment: str
    network_zone: str
    status: AssetStatus
    risk_score: float
    criticality: Criticality
    first_seen: datetime
    last_seen: datetime
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class AssetReference(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    hostname: str
    display_name: str


class AssetFilters(BaseModel):
    asset_type: AssetType | None = None
    status: AssetStatus | None = None
    network_zone: str | None = Field(default=None, max_length=64)
    criticality: Criticality | None = None
    min_risk_score: float | None = Field(default=None, ge=0, le=100)
    search: str | None = Field(default=None, min_length=1, max_length=255)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)
