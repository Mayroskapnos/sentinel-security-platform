import json
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from app.core.config import Settings, get_settings
from app.investigation.config import assistant_configuration
from app.investigation.prompts import PromptEnvelope
from app.schemas.investigation import (
    InvestigationAction,
    InvestigationContext,
    InvestigationKeyAsset,
    InvestigationObservation,
    InvestigationOutput,
    InvestigationQuestionOutput,
    InvestigationUncertainty,
)


class ProviderError(Exception):
    """A safe provider error that never contains credentials or request evidence."""


@dataclass(frozen=True)
class ProviderUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None


@dataclass(frozen=True)
class AnalysisProviderResult:
    output: InvestigationOutput
    usage: ProviderUsage = ProviderUsage()


@dataclass(frozen=True)
class QuestionProviderResult:
    output: InvestigationQuestionOutput
    usage: ProviderUsage = ProviderUsage()


class InvestigationProvider(Protocol):
    provider: str
    provider_label: str
    model: str

    async def analyze_incident(
        self, context: InvestigationContext, prompt: PromptEnvelope
    ) -> AnalysisProviderResult: ...

    async def answer_question(
        self,
        context: InvestigationContext,
        question: str,
        recent_messages: list[dict[str, Any]],
        prompt: PromptEnvelope,
    ) -> QuestionProviderResult: ...


class MockInvestigationProvider:
    """Deterministic local provider for development and CI; it makes no external calls."""

    provider = "mock"
    provider_label = "Mock Investigation Provider"

    def __init__(self, model: str = "sentinel-mock-v1") -> None:
        self.model = model

    async def analyze_incident(
        self, context: InvestigationContext, prompt: PromptEnvelope
    ) -> AnalysisProviderResult:
        del prompt
        incident = context.incident
        incident_ref = str(incident["ref"])
        stages = [str(item["stage"]).replace("_", " ") for item in context.deterministic_story]
        stage_text = ", ".join(dict.fromkeys(stages)) or "security alert activity"
        summary = (
            f"SENTINEL correlated {incident['alert_count']} alerts involving "
            f"{incident['asset_count']} assets. Persisted evidence records {stage_text}. "
            "This analysis does not prove credential theft, host compromise, database "
            "collection, or data exfiltration."
        )
        observations = [
            InvestigationObservation(
                statement=str(item["description"]),
                evidence_refs=self._story_refs(item, context),
            )
            for item in context.deterministic_story[:8]
        ]
        if not observations:
            observations = [
                InvestigationObservation(
                    statement="SENTINEL recorded an evidence-backed Incident.",
                    evidence_refs=[incident_ref],
                )
            ]
        correlation_descriptions = [
            str(signal.get("description", ""))
            for signal in context.correlation_evidence
            if signal.get("description")
        ]
        correlation_text = (
            " ".join(dict.fromkeys(correlation_descriptions))
            or "The first alert established the Incident; no cross-alert signals exist yet."
        )
        alert_refs = [str(alert["ref"]) for alert in context.alerts[:8]] or [incident_ref]
        key_assets = [
            InvestigationKeyAsset(
                asset_ref=str(asset["ref"]),
                reason=(
                    f"{asset['hostname']} is an affected {asset['asset_type']} with "
                    f"{asset['criticality']} criticality."
                ),
            )
            for asset in context.assets[:6]
        ]
        uncertainties = self._uncertainties(context, incident_ref)
        actions = self._actions(context, incident_ref)
        return AnalysisProviderResult(
            output=InvestigationOutput(
                executive_summary=summary,
                observations=observations,
                correlation_explanation=InvestigationObservation(
                    statement=correlation_text[:1000],
                    evidence_refs=alert_refs,
                ),
                key_assets=key_assets,
                uncertainties=uncertainties,
                recommended_actions=actions,
            )
        )

    async def answer_question(
        self,
        context: InvestigationContext,
        question: str,
        recent_messages: list[dict[str, Any]],
        prompt: PromptEnvelope,
    ) -> QuestionProviderResult:
        del recent_messages, prompt
        normalized = question.lower()
        incident_ref = str(context.incident["ref"])
        if any(term in normalized for term in ("weather", "sports", "recipe", "stock price")):
            return self._question(
                "The Investigation Assistant is limited to evidence from this Incident and "
                "cannot answer unrelated questions.",
                [incident_ref],
                ["No external information was queried."],
            )
        if any(
            term in normalized
            for term in ("block ", "isolate ", "disable ", "run another attack", "scan ")
        ):
            return self._question(
                "The Investigation Assistant cannot execute containment, simulations, scans, "
                "or account changes. An analyst can review the cited Incident evidence before "
                "using the appropriate authorized control.",
                [incident_ref],
                ["No action was executed."],
            )
        if any(term in normalized for term in ("exfil", "steal data", "stole data", "data theft")):
            database_items = [
                item
                for item in context.deterministic_story
                if item.get("stage") == "database_access"
            ]
            refs = (
                self._story_refs(database_items[0], context) if database_items else [incident_ref]
            )
            return self._question(
                "SENTINEL has no evidence proving data theft or exfiltration. "
                + (
                    "The Incident contains an unexpected database connection, but that does "
                    "not establish database queries, collection, or exfiltration."
                    if database_items
                    else "No authoritative database-collection evidence is present."
                ),
                refs,
                ["Packet contents and database query results are not available."],
            )
        if "why" in normalized and any(
            term in normalized for term in ("correlat", "one incident", "group")
        ):
            reasons = [
                str(item.get("description"))
                for item in context.correlation_evidence
                if item.get("description")
            ]
            return self._question(
                "SENTINEL grouped the alerts using deterministic evidence: "
                + (" ".join(dict.fromkeys(reasons)) or "the first alert established the Incident."),
                [str(alert["ref"]) for alert in context.alerts[:8]] or [incident_ref],
                ["The correlation confidence is deterministic, not a probability."],
            )
        if "first" in normalized and context.deterministic_story:
            first = context.deterministic_story[0]
            return self._question(
                f"The first persisted story item is: {first['description']}",
                self._story_refs(first, context),
                ["Ordering follows persisted source timestamps."],
            )
        if "asset" in normalized and context.assets:
            ranked = sorted(
                context.assets,
                key=lambda item: (
                    {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(
                        str(item["criticality"]), 0
                    ),
                    float(item["risk_score"]),
                ),
                reverse=True,
            )
            asset = ranked[0]
            return self._question(
                f"Prioritize review of {asset['hostname']} because it has "
                f"{asset['criticality']} criticality and is linked to this Incident.",
                [str(asset["ref"]), incident_ref],
                ["This is an investigation priority, not an automated response decision."],
            )
        return self._question(
            "The available Incident evidence supports reviewing the deterministic story, "
            "associated alerts, and affected assets. SENTINEL cannot establish conclusions "
            "beyond that bounded evidence.",
            [incident_ref],
            ["Ask about observed activity, correlation, assets, evidence, or uncertainty."],
        )

    @staticmethod
    def _story_refs(item: dict[str, Any], context: InvestigationContext) -> list[str]:
        candidates = [
            item.get("alert_ref"),
            *(item.get("event_refs") or []),
            *(item.get("asset_refs") or []),
            item.get("network_connection_ref"),
        ]
        return [
            str(reference)
            for reference in dict.fromkeys(candidates)
            if reference and reference in context.evidence_catalog
        ][:12]

    @staticmethod
    def _uncertainties(
        context: InvestigationContext, incident_ref: str
    ) -> list[InvestigationUncertainty]:
        items = [
            InvestigationUncertainty(
                statement="SENTINEL cannot determine whether observed access was authorized.",
                reason="Authorization intent is not present in the supplied telemetry.",
                evidence_refs=[incident_ref],
            )
        ]
        database = next(
            (
                item
                for item in context.deterministic_story
                if item.get("stage") == "database_access"
            ),
            None,
        )
        if database:
            items.append(
                InvestigationUncertainty(
                    statement="No evidence proves database collection or data exfiltration.",
                    reason="The observed database evidence establishes a connection only.",
                    evidence_refs=MockInvestigationProvider._story_refs(database, context),
                )
            )
        return items

    @staticmethod
    def _actions(context: InvestigationContext, incident_ref: str) -> list[InvestigationAction]:
        actions = [
            InvestigationAction(
                priority="high",
                action="Review authentication activity associated with this Incident.",
                reason="Confirm whether the observed identities and access were expected.",
                evidence_refs=[incident_ref],
            ),
            InvestigationAction(
                priority="medium",
                action="Preserve the cited alert and event evidence for analyst review.",
                reason=(
                    "Preservation supports a reproducible investigation without changing systems."
                ),
                evidence_refs=[incident_ref],
            ),
        ]
        database = next(
            (
                item
                for item in context.deterministic_story
                if item.get("stage") == "database_access"
            ),
            None,
        )
        if database:
            actions.append(
                InvestigationAction(
                    priority="high",
                    action="Review database connection history and authorized-use records.",
                    reason=(
                        "An unexpected database connection was observed, but query activity "
                        "is unknown."
                    ),
                    evidence_refs=MockInvestigationProvider._story_refs(database, context),
                )
            )
        return actions

    @staticmethod
    def _question(
        answer: str, evidence_refs: list[str], limitations: list[str]
    ) -> QuestionProviderResult:
        return QuestionProviderResult(
            output=InvestigationQuestionOutput(
                answer=answer,
                evidence_refs=evidence_refs,
                limitations=limitations,
            )
        )


class OpenAIInvestigationProvider:
    """Small Responses API adapter with Structured Outputs and no provider-side storage."""

    provider = "openai"
    provider_label = "OpenAI"

    def __init__(
        self,
        settings: Settings,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.settings = settings
        self.model = settings.sentinel_ai_model.strip()
        self.transport = transport

    async def analyze_incident(
        self, context: InvestigationContext, prompt: PromptEnvelope
    ) -> AnalysisProviderResult:
        del context
        document, usage = await self._structured_response(
            prompt, InvestigationOutput, "sentinel_investigation_analysis"
        )
        return AnalysisProviderResult(
            output=InvestigationOutput.model_validate(document), usage=usage
        )

    async def answer_question(
        self,
        context: InvestigationContext,
        question: str,
        recent_messages: list[dict[str, Any]],
        prompt: PromptEnvelope,
    ) -> QuestionProviderResult:
        del context, question, recent_messages
        document, usage = await self._structured_response(
            prompt, InvestigationQuestionOutput, "sentinel_incident_question"
        )
        return QuestionProviderResult(
            output=InvestigationQuestionOutput.model_validate(document), usage=usage
        )

    async def _structured_response(
        self,
        prompt: PromptEnvelope,
        output_model,
        schema_name: str,
    ) -> tuple[dict[str, Any], ProviderUsage]:  # noqa: ANN001
        body = {
            "model": self.model,
            "instructions": prompt.instructions,
            "input": prompt.input_text,
            "store": False,
            "max_output_tokens": 2_000,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "strict": True,
                    "schema": output_model.model_json_schema(),
                }
            },
        }
        headers = {
            "Authorization": f"Bearer {self.settings.sentinel_ai_api_key}",
            "Content-Type": "application/json",
        }
        base_url = self.settings.sentinel_ai_base_url.rstrip("/") + "/"
        try:
            async with httpx.AsyncClient(
                base_url=base_url,
                headers=headers,
                timeout=self.settings.sentinel_ai_timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.post("responses", json=body)
        except httpx.TimeoutException as exc:
            raise ProviderError("The configured AI provider timed out.") from exc
        except httpx.HTTPError as exc:
            raise ProviderError("The configured AI provider could not be reached.") from exc
        if response.status_code >= 400:
            raise ProviderError(
                f"The configured AI provider returned status {response.status_code}."
            )
        try:
            payload = response.json()
            output_text = payload.get("output_text") or self._output_text(payload)
            document = json.loads(output_text)
        except (TypeError, ValueError, KeyError) as exc:
            raise ProviderError("The configured AI provider returned malformed output.") from exc
        usage_data = payload.get("usage") or {}
        return document, ProviderUsage(
            input_tokens=self._optional_int(usage_data.get("input_tokens")),
            output_tokens=self._optional_int(usage_data.get("output_tokens")),
        )

    @staticmethod
    def _output_text(payload: dict[str, Any]) -> str:
        for item in payload.get("output", []):
            for content in item.get("content", []):
                if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                    return content["text"]
        raise KeyError("output_text")

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        return value if isinstance(value, int) and value >= 0 else None


def get_provider(settings: Settings | None = None) -> InvestigationProvider:
    settings = settings or get_settings()
    configuration = assistant_configuration(settings)
    if not configuration.enabled:
        raise ProviderError(configuration.message)
    if configuration.provider == "mock":
        return MockInvestigationProvider(configuration.model or "sentinel-mock-v1")
    return OpenAIInvestigationProvider(settings)
