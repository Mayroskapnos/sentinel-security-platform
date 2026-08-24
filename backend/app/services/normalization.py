from collections.abc import Mapping
from datetime import UTC
from typing import Any

from app.schemas.security_event import SecurityEventCreate


class EventNormalizer:
    """Normalize collector output into SENTINEL's canonical event contract."""

    _NORMALIZED_TEXT_FIELDS = ("event_type", "source", "action", "status")

    @classmethod
    def normalize(cls, payload: Mapping[str, Any]) -> SecurityEventCreate:
        candidate = dict(payload)
        for field in cls._NORMALIZED_TEXT_FIELDS:
            value = candidate.get(field)
            if isinstance(value, str):
                candidate[field] = value.strip().lower()

        event = SecurityEventCreate.model_validate(candidate)
        event.timestamp = event.timestamp.astimezone(UTC)
        if event.hostname:
            event.hostname = event.hostname.strip().lower()
        if event.username:
            event.username = event.username.strip()
        return event
