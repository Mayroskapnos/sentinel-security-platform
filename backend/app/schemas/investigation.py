import re
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import as_utc

AnalysisStatus = Literal["pending", "running", "completed", "failed"]
AssistantMode = Literal["disabled", "mock", "configured", "unavailable"]
EvidenceKind = Literal["incident", "alert", "event", "asset", "connection", "scenario"]
ActionPriority = Literal["critical", "high", "medium", "low"]
EVIDENCE_REF_PATTERN = re.compile(
    r"^(incident|alert|event|asset|connection|scenario):"
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


class AssistantStatus(BaseModel):
    enabled: bool
    mode: AssistantMode
    provider: str | None
    provider_label: str
    model: str | None
    external: bool
    message: str


class EvidenceReference(BaseModel):
    ref: str
    kind: EvidenceKind
    id: UUID
    label: str


class InvestigationObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    statement: str = Field(min_length=1, max_length=1000)
    evidence_refs: list[str] = Field(min_length=1, max_length=12)

    @field_validator("evidence_refs")
    @classmethod
    def valid_refs(cls, values: list[str]) -> list[str]:
        if any(not EVIDENCE_REF_PATTERN.fullmatch(value) for value in values):
            raise ValueError("evidence references must use a supported kind and UUID")
        return list(dict.fromkeys(values))


class InvestigationUncertainty(BaseModel):
    model_config = ConfigDict(extra="forbid")

    statement: str = Field(min_length=1, max_length=1000)
    reason: str = Field(min_length=1, max_length=1000)
    evidence_refs: list[str] = Field(min_length=1, max_length=12)

    @field_validator("evidence_refs")
    @classmethod
    def valid_refs(cls, values: list[str]) -> list[str]:
        if any(not EVIDENCE_REF_PATTERN.fullmatch(value) for value in values):
            raise ValueError("evidence references must use a supported kind and UUID")
        return list(dict.fromkeys(values))


class InvestigationAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    priority: ActionPriority
    action: str = Field(min_length=1, max_length=1000)
    reason: str = Field(min_length=1, max_length=1000)
    evidence_refs: list[str] = Field(min_length=1, max_length=12)

    @field_validator("evidence_refs")
    @classmethod
    def valid_refs(cls, values: list[str]) -> list[str]:
        if any(not EVIDENCE_REF_PATTERN.fullmatch(value) for value in values):
            raise ValueError("evidence references must use a supported kind and UUID")
        return list(dict.fromkeys(values))


class InvestigationKeyAsset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_ref: str
    reason: str = Field(min_length=1, max_length=1000)

    @field_validator("asset_ref")
    @classmethod
    def valid_asset_ref(cls, value: str) -> str:
        if not value.startswith("asset:") or not EVIDENCE_REF_PATTERN.fullmatch(value):
            raise ValueError("key assets require a valid asset evidence reference")
        return value


class InvestigationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    executive_summary: str = Field(min_length=20, max_length=2000)
    observations: list[InvestigationObservation] = Field(min_length=1, max_length=12)
    correlation_explanation: InvestigationObservation
    key_assets: list[InvestigationKeyAsset] = Field(max_length=10)
    uncertainties: list[InvestigationUncertainty] = Field(min_length=1, max_length=10)
    recommended_actions: list[InvestigationAction] = Field(min_length=1, max_length=10)

    @field_validator("executive_summary")
    @classmethod
    def bounded_sentences(cls, value: str) -> str:
        sentence_count = len(re.findall(r"[.!?](?:\s|$)", value.strip()))
        if not 2 <= sentence_count <= 5:
            raise ValueError("executive summary must contain between two and five sentences")
        return value


class InvestigationQuestionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str = Field(min_length=1, max_length=3000)
    evidence_refs: list[str] = Field(min_length=1, max_length=12)
    limitations: list[str] = Field(max_length=5)

    @field_validator("evidence_refs")
    @classmethod
    def valid_refs(cls, values: list[str]) -> list[str]:
        if any(not EVIDENCE_REF_PATTERN.fullmatch(value) for value in values):
            raise ValueError("evidence references must use a supported kind and UUID")
        return list(dict.fromkeys(values))


class InvestigationContext(BaseModel):
    context_version: Literal["1"] = "1"
    incident: dict[str, Any]
    assets: list[dict[str, Any]]
    alerts: list[dict[str, Any]]
    deterministic_story: list[dict[str, Any]]
    observed_attack_techniques: list[dict[str, Any]]
    correlation_evidence: list[dict[str, Any]]
    network_relationships: list[dict[str, Any]]
    key_events: list[dict[str, Any]]
    scenario_context: dict[str, Any] | None
    evidence_catalog: dict[str, str]


class InvestigationAnalysisListItem(BaseModel):
    id: UUID
    incident_id: UUID
    status: AnalysisStatus
    provider: str
    provider_label: str
    model: str
    requested_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    analysis_version: str
    context_hash: str
    is_stale: bool
    input_tokens: int | None
    output_tokens: int | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    @field_validator(
        "requested_at",
        "started_at",
        "completed_at",
        "created_at",
        "updated_at",
    )
    @classmethod
    def utc_timestamp(cls, value: datetime | None) -> datetime | None:
        return as_utc(value) if value else None


class InvestigationAnalysisResponse(InvestigationAnalysisListItem):
    output: InvestigationOutput | None
    evidence_catalog: dict[str, str]


class InvestigationQuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)

    @field_validator("question")
    @classmethod
    def nonblank(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("question must not be blank")
        return normalized


class InvestigationMessageResponse(BaseModel):
    id: UUID
    incident_id: UUID
    analysis_id: UUID | None
    reply_to_id: UUID | None
    role: Literal["user", "assistant"]
    content: str
    evidence_refs: list[str]
    context_hash: str
    provider: str | None
    model: str | None
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        return as_utc(value)


class InvestigationQuestionResponse(BaseModel):
    question: InvestigationMessageResponse
    answer: InvestigationMessageResponse
    evidence_catalog: dict[str, str]
