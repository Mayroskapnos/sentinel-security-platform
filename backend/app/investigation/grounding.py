import re
from typing import Any

from app.schemas.investigation import (
    InvestigationContext,
    InvestigationOutput,
    InvestigationQuestionOutput,
)

TECHNIQUE_PATTERN = re.compile(r"\bT\d{4}(?:\.\d{3})?\b", re.IGNORECASE)
SENTINEL_HOSTNAME_PATTERN = re.compile(
    r"\b(?:employee-\d+|web-server|admin-server|domain-controller|database-\d+)\b",
    re.IGNORECASE,
)
COUNT_PATTERNS = {
    "alert_count": re.compile(r"\b(\d+)\s+alerts?\b", re.IGNORECASE),
    "asset_count": re.compile(r"\b(\d+)\s+assets?\b", re.IGNORECASE),
}
UNSUPPORTED_CLAIMS = (
    re.compile(r"\bcredentials? (?:were |was )?stolen\b", re.IGNORECASE),
    re.compile(r"\bhost (?:was |is )?compromised\b", re.IGNORECASE),
    re.compile(r"\bdatabase (?:was )?queried\b", re.IGNORECASE),
    re.compile(r"\brecords? (?:were |was )?stolen\b", re.IGNORECASE),
    re.compile(r"\bdata (?:was |were )?exfiltrated\b", re.IGNORECASE),
    re.compile(r"\bdata exfiltration (?:occurred|was confirmed)\b", re.IGNORECASE),
)
NEGATION_MARKERS = (
    "no evidence",
    "does not",
    "do not",
    "cannot",
    "not prove",
    "not establish",
    "not confirmed",
    "unknown",
    "uncertain",
)


class GroundingError(Exception):
    """Provider output failed deterministic SENTINEL evidence validation."""


def validate_analysis_output(
    output: InvestigationOutput, context: InvestigationContext
) -> InvestigationOutput:
    sanitized = InvestigationOutput.model_validate(_sanitize(output.model_dump()))
    refs: list[str] = []
    for observation in sanitized.observations:
        refs.extend(observation.evidence_refs)
    refs.extend(sanitized.correlation_explanation.evidence_refs)
    refs.extend(asset.asset_ref for asset in sanitized.key_assets)
    for uncertainty in sanitized.uncertainties:
        refs.extend(uncertainty.evidence_refs)
    for action in sanitized.recommended_actions:
        refs.extend(action.evidence_refs)
    _validate_refs(refs, context)
    _validate_text_fields(sanitized.model_dump(), context)
    return sanitized


def validate_question_output(
    output: InvestigationQuestionOutput, context: InvestigationContext
) -> InvestigationQuestionOutput:
    sanitized = InvestigationQuestionOutput.model_validate(_sanitize(output.model_dump()))
    _validate_refs(sanitized.evidence_refs, context)
    _validate_text_fields(sanitized.model_dump(), context)
    return sanitized


def _validate_refs(refs: list[str], context: InvestigationContext) -> None:
    unsupported = sorted(set(refs) - set(context.evidence_catalog))
    if unsupported:
        raise GroundingError("Provider output referenced evidence outside the Incident context.")


def _validate_text(text: str, context: InvestigationContext) -> None:
    authorized_techniques = {
        str(item["technique_id"]).upper()
        for item in context.observed_attack_techniques
        if item.get("technique_id")
    }
    mentioned = {match.upper() for match in TECHNIQUE_PATTERN.findall(text)}
    if mentioned - authorized_techniques:
        raise GroundingError("Provider output introduced an unsupported ATT&CK technique.")
    known_hostnames = {str(asset.get("hostname", "")).lower() for asset in context.assets}
    mentioned_hostnames = {match.lower() for match in SENTINEL_HOSTNAME_PATTERN.findall(text)}
    if mentioned_hostnames - known_hostnames:
        raise GroundingError("Provider output introduced an unsupported Asset identity.")
    for field, pattern in COUNT_PATTERNS.items():
        expected = int(context.incident[field])
        if any(int(value) != expected for value in pattern.findall(text)):
            raise GroundingError("Provider output contradicted an authoritative Incident count.")
    lowered = text.lower()
    for pattern in UNSUPPORTED_CLAIMS:
        for match in pattern.finditer(text):
            prefix = lowered[max(0, match.start() - 80) : match.start()]
            if not any(marker in prefix for marker in NEGATION_MARKERS):
                raise GroundingError("Provider output made an unsupported security conclusion.")


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, str):
        return "".join(
            character for character in value.strip() if character >= " " or character in "\n\t"
        )
    return value


def _text_fields(value: Any):  # noqa: ANN202
    if isinstance(value, dict):
        for item in value.values():
            yield from _text_fields(item)
    if isinstance(value, list):
        for item in value:
            yield from _text_fields(item)
    if isinstance(value, str):
        yield value


def _validate_text_fields(value: Any, context: InvestigationContext) -> None:
    for text in _text_fields(value):
        _validate_text(text, context)
