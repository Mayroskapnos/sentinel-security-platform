import json
from pathlib import Path

import pytest

from app.collector.adapters import (
    DatabaseClientConnectionAdapter,
    LinuxAuthAdapter,
    NetworkConnectionAdapter,
    PostgresAdapter,
    ProcessAdapter,
    SudoAdapter,
    WebAccessAdapter,
    WebAuthenticationAdapter,
)
from app.collector.checkpoint import CheckpointStore
from app.collector.registry import Source

TIMESTAMP = "2026-08-25T10:15:30+03:00"


def test_web_access_normalization_preserves_source_time_and_raw_evidence() -> None:
    event = WebAccessAdapter().parse(
        {
            "kind": "http_request",
            "timestamp": TIMESTAMP,
            "method": "GET",
            "path": "/api/profile",
            "status_code": 200,
            "client_ip": "10.10.20.10",
            "client_port": 49152,
            "destination_ip": "10.10.10.10",
            "duration_ms": 4.2,
        }
    )

    assert event.timestamp.isoformat() == "2026-08-25T07:15:30+00:00"
    assert event.event_type == "http_request"
    assert event.source == "web_access"
    assert event.action == "GET /api/profile"
    assert event.raw_event["status_code"] == 200
    assert event.normalized_data["origin"] == "corporate_lab"


def test_failed_web_login_is_authentication_without_password_evidence() -> None:
    event = WebAuthenticationAdapter().parse(
        {
            "kind": "web_authentication",
            "timestamp": TIMESTAMP,
            "client_ip": "10.10.20.10",
            "username": "demo-user",
            "password": "must-not-survive",
            "result": "failed",
        }
    )

    assert event.event_type == "authentication"
    assert event.source == "web_application"
    assert event.status == "failed"
    assert event.raw_event["password"] == "[REDACTED]"


@pytest.mark.parametrize(
    ("result", "expected"),
    [("Accepted", "success"), ("Failed", "failed")],
)
def test_real_ssh_log_normalization(result: str, expected: str) -> None:
    message = f"sshd[42]: {result} password for admin-demo from 10.10.20.10 port 50123 ssh2"
    event = LinuxAuthAdapter().parse(
        {
            "kind": "linux_auth",
            "timestamp": TIMESTAMP,
            "hostname": "admin-server",
            "destination_ip": "10.10.30.10",
            "message": message,
        }
    )

    assert event.action == "ssh_login"
    assert event.status == expected
    assert event.source_ip == "10.10.20.10"
    assert event.destination_ip == "10.10.30.10"
    assert event.username == "admin-demo"


def test_process_sudo_and_network_normalization() -> None:
    process = ProcessAdapter().parse(
        {
            "kind": "process_execution",
            "timestamp": TIMESTAMP,
            "hostname": "employee-01",
            "source_ip": "10.10.20.10",
            "username": "demo-user",
            "executable": "/usr/bin/whoami",
            "return_code": 0,
        }
    )
    sudo = SudoAdapter().parse(
        {
            "kind": "sudo_execution",
            "timestamp": TIMESTAMP,
            "hostname": "admin-server",
            "source_ip": "10.10.30.10",
            "username": "admin-demo",
            "command": "/usr/bin/id",
            "target_user": "root",
            "return_code": 0,
        }
    )
    network = NetworkConnectionAdapter().parse(
        {
            "kind": "network_connection",
            "timestamp": TIMESTAMP,
            "hostname": "employee-01",
            "source_ip": "10.10.20.10",
            "destination_ip": "10.10.10.10",
            "destination_port": 8080,
            "process_name": "curl",
            "result": "success",
        }
    )

    assert process.event_type == "process_execution"
    assert process.process_name == "/usr/bin/whoami"
    assert sudo.event_type == "privilege"
    assert sudo.action == "sudo_command"
    assert sudo.status == "success"
    assert network.event_type == "network_connection"
    assert network.destination_port == 8080


def test_database_connection_does_not_assert_collection() -> None:
    event = PostgresAdapter({"10.10.30.30": "10.10.10.10"}).parse(
        {
            "timestamp": TIMESTAMP,
            "user": "lab_app",
            "dbname": "corp_demo",
            "remote_host": "10.10.30.30",
            "remote_port": 41234,
            "session_id": "abc",
            "message": "connection authorized: user=lab_app database=corp_demo",
        }
    )

    assert event is not None
    assert event.event_type == "database_connection"
    assert event.status == "success"
    assert event.source_ip == "10.10.10.10"
    assert event.normalized_data["connection_evidence"] is True
    assert event.normalized_data["data_collection_asserted"] is False


def test_actual_database_client_result_is_connection_only_evidence() -> None:
    event = DatabaseClientConnectionAdapter().parse(
        {
            "kind": "database_client_connection",
            "timestamp": TIMESTAMP,
            "hostname": "employee-01",
            "source_ip": "10.10.20.10",
            "destination_ip": "10.10.30.20",
            "destination_port": 5432,
            "username": "demo-user",
            "database": "corp_demo",
            "result": "success",
        }
    )

    assert event.event_type == "database_connection"
    assert event.source == "database_client"
    assert event.normalized_data["connection_evidence"] is True
    assert event.normalized_data["data_collection_asserted"] is False


def test_structured_and_postgres_events_preserve_explicit_scenario_attribution() -> None:
    run_id = "1a7a65a3-4cb0-4fa6-a2ea-1e266594ee8d"
    network = NetworkConnectionAdapter().parse(
        {
            "kind": "network_connection",
            "timestamp": TIMESTAMP,
            "hostname": "employee-01",
            "source_ip": "10.10.20.10",
            "destination_ip": "10.10.20.20",
            "destination_port": 8080,
            "process_name": "lab-service-check",
            "result": "success",
            "scenario_run_id": run_id,
            "scenario_id": "SCN-005",
        }
    )
    database = PostgresAdapter().parse(
        {
            "timestamp": TIMESTAMP,
            "user": "lab_app",
            "dbname": "corp_demo",
            "remote_host": "10.10.20.10",
            "application_name": f"sentinel-sim:{run_id}:SCN-005",
            "message": "connection authorized: user=lab_app database=corp_demo",
        }
    )

    assert str(network.scenario_run_id) == run_id
    assert network.normalized_data["scenario_id"] == "SCN-005"
    assert database is not None
    assert str(database.scenario_run_id) == run_id
    assert database.scenario_id == "SCN-005"
    assert database.normalized_data["data_collection_asserted"] is False


def test_postgresql_native_timestamp_and_local_healthcheck_are_supported() -> None:
    adapter = PostgresAdapter()
    event = adapter.parse(
        {
            "timestamp": "2026-08-25 09:20:24.254 UTC",
            "user": "lab_app",
            "dbname": "corp_demo",
            "remote_host": "10.10.20.10",
            "message": "connection authorized: user=lab_app database=corp_demo",
        }
    )

    assert event is not None
    assert event.timestamp.isoformat() == "2026-08-25T09:20:24.254000+00:00"
    assert (
        adapter.parse(
            {
                "timestamp": "2026-08-25 09:20:24.254 UTC",
                "remote_host": "[local]",
                "message": "connection authorized: user=lab_admin database=corp_demo",
            }
        )
        is None
    )


def test_postgresql_native_duration_statement_becomes_query_telemetry() -> None:
    event = PostgresAdapter().parse(
        {
            "timestamp": "2026-08-25 09:27:10.212 UTC",
            "user": "lab_app",
            "dbname": "corp_demo",
            "remote_host": "10.10.20.10",
            "remote_port": 59414,
            "session_id": "abc",
            "ps": "SELECT",
            "message": "duration: 0.367 ms  statement: SELECT current_database();",
        }
    )

    assert event is not None
    assert event.event_type == "database_query"
    assert event.action == "database_query"
    assert event.normalized_data["query_category"] == "select"
    assert event.normalized_data["query_observed"] is True


def test_malformed_source_record_is_rejected() -> None:
    source = Source("web", Path("unused"), {"http_request": WebAccessAdapter()})
    with pytest.raises(ValueError):
        source.parse_line("not-json")
    with pytest.raises(ValueError, match="unsupported web record kind"):
        source.parse_line(json.dumps({"kind": "unknown"}))


@pytest.mark.asyncio
async def test_checkpoint_prevents_replay_and_resets_for_replaced_file(tmp_path: Path) -> None:
    store = CheckpointStore(tmp_path / "state" / "checkpoints.json")
    source = tmp_path / "events.jsonl"
    source.write_text("one\n", encoding="utf-8")

    await store.save(source, "device:inode", 4)

    reloaded = CheckpointStore(tmp_path / "state" / "checkpoints.json")
    assert reloaded.get(source, "device:inode", 4) == 4
    assert reloaded.get(source, "replacement:inode", 4) == 0
    assert reloaded.get(source, "device:inode", 2) == 0
