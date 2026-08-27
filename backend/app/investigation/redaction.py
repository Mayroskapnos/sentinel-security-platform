import json
import re
from typing import Any

REDACTED = "[REDACTED]"
SENSITIVE_KEY = re.compile(
    r"(?:password|passwd|pwd|token|api[_-]?key|authorization|cookie|secret|credential)",
    re.IGNORECASE,
)
INLINE_SECRET_PATTERNS = (
    re.compile(r"(?i)(authorization\s*[:=]\s*(?:bearer\s+)?)([^\s,;\]}]+)"),
    re.compile(
        r"(?i)\b(password|passwd|pwd|token|api[_-]?key|secret)\s*[:=]\s*"
        r"([^\s,;\]}]+)"
    ),
    re.compile(r"(?i)(cookie\s*:\s*)([^\r\n]+)"),
)


def redact_text(value: str) -> str:
    redacted = value
    for index, pattern in enumerate(INLINE_SECRET_PATTERNS):
        if index == 1:
            redacted = pattern.sub(lambda match: f"{match.group(1)}={REDACTED}", redacted)
        else:
            redacted = pattern.sub(lambda match: f"{match.group(1)}{REDACTED}", redacted)
    return redacted


def redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): REDACTED if SENSITIVE_KEY.search(str(key)) else redact_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, tuple):
        return [redact_value(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def bounded_redacted_json(value: Any, max_characters: int = 1_000) -> str:
    serialized = json.dumps(
        redact_value(value),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        default=str,
    )
    return serialized[:max_characters]
