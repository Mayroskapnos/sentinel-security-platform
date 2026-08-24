from datetime import UTC, datetime


def asset_payload(
    hostname: str = "test-host",
    ip_address: str = "10.10.20.50",
    **overrides,
) -> dict:
    payload = {
        "hostname": hostname,
        "display_name": hostname.replace("-", " ").title(),
        "ip_address": ip_address,
        "mac_address": "02:42:0a:0a:14:32",
        "asset_type": "workstation",
        "operating_system": "Ubuntu 24.04",
        "environment": "test",
        "network_zone": "employee",
        "status": "online",
        "risk_score": 25,
        "criticality": "medium",
        "first_seen": "2026-08-20T10:00:00Z",
        "last_seen": "2026-08-24T10:00:00Z",
        "metadata_json": {"test": True},
    }
    payload.update(overrides)
    return payload


def event_payload(
    timestamp: datetime | str | None = None,
    hostname: str = "test-host",
    **overrides,
) -> dict:
    timestamp_value = timestamp or datetime.now(UTC)
    payload = {
        "timestamp": (
            timestamp_value.isoformat()
            if isinstance(timestamp_value, datetime)
            else timestamp_value
        ),
        "event_type": "authentication",
        "source": "linux_auth",
        "source_ip": "10.10.50.2",
        "destination_ip": "10.10.20.50",
        "source_port": 45000,
        "destination_port": 22,
        "hostname": hostname,
        "username": "demo-user",
        "process_name": "sshd",
        "action": "ssh_login",
        "status": "failed",
        "severity": "medium",
        "raw_event": {"result": "failure"},
        "normalized_data": {"service": "ssh"},
    }
    payload.update(overrides)
    return payload
