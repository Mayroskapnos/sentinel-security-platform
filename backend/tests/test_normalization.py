from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.services.normalization import EventNormalizer


def test_normalizer_canonicalizes_text_and_utc() -> None:
    event = EventNormalizer.normalize(
        {
            "timestamp": "2026-08-24T16:22:17+02:00",
            "event_type": " Authentication ",
            "source": " LINUX_AUTH ",
            "hostname": " Employee-01 ",
            "action": " SSH_Login ",
            "status": " Failed ",
            "severity": "low",
        }
    )
    assert event.timestamp == datetime(2026, 8, 24, 14, 22, 17, tzinfo=UTC)
    assert event.event_type == "authentication"
    assert event.source == "linux_auth"
    assert event.hostname == "employee-01"
    assert event.action == "ssh_login"


def test_normalizer_preserves_source_specific_evidence() -> None:
    event = EventNormalizer.normalize(
        {
            "timestamp": "2026-08-24T14:22:17Z",
            "event_type": "authentication",
            "source": "linux_auth",
            "action": "ssh_login",
            "status": "failed",
            "raw_event": {"pam_result": 7},
            "normalized_data": {"service": "ssh"},
        }
    )
    assert event.raw_event == {"pam_result": 7}
    assert event.normalized_data == {"service": "ssh"}


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {
            "timestamp": "not-a-date",
            "event_type": "authentication",
            "source": "linux_auth",
            "action": "login",
            "status": "failed",
        },
    ],
)
def test_normalizer_rejects_malformed_input(payload: dict) -> None:
    with pytest.raises(ValidationError):
        EventNormalizer.normalize(payload)
