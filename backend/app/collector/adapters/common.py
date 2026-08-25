from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from app.schemas.security_event import SecurityEventCreate

REDACTED_KEYS = {"password", "secret", "token", "authorization", "collector_key"}


def timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("source record requires an ISO 8601 timestamp")
    normalized = value.replace(" UTC", "+00:00").replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("source timestamp must include timezone information")
    return parsed.astimezone(UTC)


def optional_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): "[REDACTED]" if str(key).lower() in REDACTED_KEYS else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def event(**values: Any) -> SecurityEventCreate:
    raw_event = values.get("raw_event")
    scenario_run_id = values.get("scenario_run_id")
    scenario_id = values.get("scenario_id")
    if isinstance(raw_event, Mapping):
        scenario_run_id = raw_event.get("scenario_run_id") or scenario_run_id
        scenario_id = raw_event.get("scenario_id") or scenario_id
    normalized_data = {
        "origin": "corporate_lab",
        "lab_version": "0.1",
        **({"scenario_run_id": scenario_run_id} if scenario_run_id else {}),
        **({"scenario_id": scenario_id} if scenario_id else {}),
        **values.pop("normalized_data", {}),
    }
    return SecurityEventCreate.model_validate(
        {
            "source_ip": None,
            "destination_ip": None,
            "source_port": None,
            "destination_port": None,
            "hostname": None,
            "username": None,
            "process_name": None,
            "severity": "informational",
            "raw_event": {},
            "scenario_run_id": scenario_run_id,
            "scenario_id": scenario_id,
            **values,
            "normalized_data": normalized_data,
        }
    )
