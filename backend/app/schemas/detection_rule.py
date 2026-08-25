from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import EventSeverity, RuleType
from app.schemas.common import as_utc

GROUP_FIELDS = {
    "asset_id",
    "source_ip",
    "destination_ip",
    "hostname",
    "username",
    "action",
}
MATCH_FIELDS = {
    "event_type",
    "source",
    "source_ip",
    "destination_ip",
    "hostname",
    "username",
    "process_name",
    "action",
    "status",
    "severity",
}


class RuleMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: str = Field(min_length=1, max_length=64)
    source: str | None = Field(default=None, max_length=64)
    source_ip: str | None = Field(default=None, max_length=45)
    destination_ip: str | None = Field(default=None, max_length=45)
    hostname: str | None = Field(default=None, max_length=255)
    username: str | None = Field(default=None, max_length=255)
    process_name: str | None = Field(default=None, max_length=255)
    action: str | None = Field(default=None, max_length=128)
    status: str | None = Field(default=None, max_length=64)
    severity: EventSeverity | None = None


class ThresholdCondition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    count: int = Field(ge=1, le=10_000)
    timeframe_seconds: int = Field(ge=1, le=86_400)
    distinct_field: (
        Literal["source_ip", "destination_ip", "source_port", "destination_port"] | None
    ) = None


class SequenceCondition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preceding: RuleMatch
    count: int = Field(ge=1, le=10_000)
    timeframe_seconds: int = Field(ge=1, le=86_400)


class RuleContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_asset_type: str | None = Field(default=None, max_length=32)
    source_network_zone: str | None = Field(default=None, max_length=64)
    destination_asset_type: str | None = Field(default=None, max_length=32)
    destination_network_zone: str | None = Field(default=None, max_length=64)


class MitreMapping(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tactic: str = Field(min_length=1, max_length=128)
    technique_id: str = Field(min_length=1, max_length=32)
    technique_name: str = Field(min_length=1, max_length=255)


class BundledRuleDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, use_enum_values=True)

    rule_id: str = Field(alias="id", pattern=r"^DET-[A-Z]+-[0-9]{3}$", max_length=64)
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=2000)
    rule_type: RuleType = Field(alias="type")
    severity: EventSeverity
    enabled: bool = True
    match: RuleMatch
    group_by: list[str] = Field(default_factory=list, max_length=6)
    threshold: ThresholdCondition | None = None
    sequence: SequenceCondition | None = None
    suppression_seconds: int = Field(default=300, ge=0, le=86_400)
    context: RuleContext | None = None
    mitre: MitreMapping | None = None

    @field_validator("group_by")
    @classmethod
    def valid_group_fields(cls, value: list[str]) -> list[str]:
        invalid = sorted(set(value) - GROUP_FIELDS)
        if invalid:
            raise ValueError(f"unsupported group_by fields: {', '.join(invalid)}")
        if len(value) != len(set(value)):
            raise ValueError("group_by fields must be unique")
        return value

    @model_validator(mode="after")
    def valid_rule_shape(self) -> "BundledRuleDefinition":
        if self.rule_type == RuleType.THRESHOLD and self.threshold is None:
            raise ValueError("threshold rules require a threshold block")
        if self.rule_type == RuleType.SEQUENCE and self.sequence is None:
            raise ValueError("sequence rules require a sequence block")
        if self.rule_type != RuleType.THRESHOLD and self.threshold is not None:
            raise ValueError("only threshold rules may define a threshold block")
        if self.rule_type != RuleType.SEQUENCE and self.sequence is not None:
            raise ValueError("only sequence rules may define a sequence block")
        return self

    def stored_configuration(self) -> dict:
        return self.model_dump(
            mode="json",
            by_alias=False,
            exclude={
                "rule_id",
                "name",
                "description",
                "rule_type",
                "severity",
                "enabled",
                "mitre",
            },
            exclude_none=True,
        )


class DetectionRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    rule_id: str
    name: str
    description: str
    rule_type: RuleType
    severity: EventSeverity
    enabled: bool
    event_type: str | None
    configuration: dict
    mitre_tactic: str | None
    mitre_technique_id: str | None
    mitre_technique_name: str | None
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at")
    @classmethod
    def utc_database_timestamp(cls, value: datetime) -> datetime:
        return as_utc(value)


class DetectionRuleFilters(BaseModel):
    enabled: bool | None = None
    rule_type: RuleType | None = None
    severity: EventSeverity | None = None
    event_type: str | None = Field(default=None, max_length=64)
    search: str | None = Field(default=None, min_length=1, max_length=255)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)


class DetectionRuleUpdate(BaseModel):
    enabled: Annotated[bool, Field(strict=True)]
