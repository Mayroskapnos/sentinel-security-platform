import re
from collections.abc import Mapping
from typing import Any

from app.collector.adapters.common import event, optional_int, redact, timestamp
from app.schemas.security_event import SecurityEventCreate

SSH_PATTERN = re.compile(
    r"(?P<result>Accepted|Failed) (?P<method>\S+) for "
    r"(?:(?:invalid user) )?(?P<username>\S+) from (?P<source_ip>\S+) "
    r"port (?P<source_port>\d+)"
)


class WebAccessAdapter:
    kind = "http_request"

    def parse(self, record: Mapping[str, Any]) -> SecurityEventCreate:
        method = str(record["method"]).upper()
        path = str(record["path"])
        status_code = int(record["status_code"])
        return event(
            timestamp=timestamp(record.get("timestamp")),
            event_type="http_request",
            source="web_access",
            source_ip=record.get("client_ip"),
            destination_ip=record.get("destination_ip", "10.10.10.10"),
            source_port=optional_int(record.get("client_port")),
            destination_port=8080,
            hostname="web-server",
            process_name="uvicorn",
            action=f"{method} {path}",
            status="success" if status_code < 400 else "failed",
            severity="informational" if status_code < 500 else "low",
            raw_event=redact(record),
            normalized_data={
                "adapter": "web_access",
                "http_method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": record.get("duration_ms"),
            },
        )


class WebAuthenticationAdapter:
    kind = "web_authentication"

    def parse(self, record: Mapping[str, Any]) -> SecurityEventCreate:
        result = str(record["result"]).lower()
        return event(
            timestamp=timestamp(record.get("timestamp")),
            event_type="authentication",
            source="web_application",
            source_ip=record.get("client_ip"),
            destination_ip=record.get("destination_ip", "10.10.10.10"),
            source_port=optional_int(record.get("client_port")),
            destination_port=8080,
            hostname="web-server",
            username=record.get("username"),
            process_name="corporate-portal",
            action="login",
            status="success" if result == "success" else "failed",
            severity="informational" if result == "success" else "low",
            raw_event=redact(record),
            normalized_data={
                "adapter": "web_authentication",
                "authentication_method": "password",
                "service": "corporate_portal",
            },
        )


class ProcessAdapter:
    kind = "process_execution"

    def parse(self, record: Mapping[str, Any]) -> SecurityEventCreate:
        return_code = int(record["return_code"])
        return event(
            timestamp=timestamp(record.get("timestamp")),
            event_type="process_execution",
            source="linux_process",
            source_ip=record.get("source_ip"),
            hostname=record.get("hostname"),
            username=record.get("username"),
            process_name=record.get("executable"),
            action="process_started",
            status="success" if return_code == 0 else "failed",
            severity="informational",
            raw_event=redact(record),
            normalized_data={
                "adapter": "process",
                "command_category": record.get("command_category", "system_utility"),
                "return_code": return_code,
            },
        )


class NetworkConnectionAdapter:
    kind = "network_connection"

    def parse(self, record: Mapping[str, Any]) -> SecurityEventCreate:
        result = str(record["result"]).lower()
        return event(
            timestamp=timestamp(record.get("timestamp")),
            event_type="network_connection",
            source="network",
            source_ip=record.get("source_ip"),
            destination_ip=record.get("destination_ip"),
            source_port=optional_int(record.get("source_port")),
            destination_port=optional_int(record.get("destination_port")),
            hostname=record.get("hostname"),
            username=record.get("username"),
            process_name=record.get("process_name"),
            action="connection_opened" if result == "success" else "connection_attempted",
            status="success" if result == "success" else "failed",
            severity="informational",
            raw_event=redact(record),
            normalized_data={
                "adapter": "network_connection",
                "protocol": record.get("protocol", "tcp"),
                "service": record.get("service"),
                "observed_destination": record.get("observed_destination"),
            },
        )


class DatabaseClientConnectionAdapter:
    kind = "database_client_connection"

    def parse(self, record: Mapping[str, Any]) -> SecurityEventCreate:
        result = str(record["result"]).lower()
        return event(
            timestamp=timestamp(record.get("timestamp")),
            event_type="database_connection",
            source="database_client",
            source_ip=record.get("source_ip"),
            destination_ip=record.get("destination_ip"),
            destination_port=optional_int(record.get("destination_port")),
            hostname=record.get("hostname"),
            username=record.get("username"),
            process_name="psql",
            action="database_connect",
            status="success" if result == "success" else "failed",
            severity="informational" if result == "success" else "low",
            raw_event=redact(record),
            normalized_data={
                "adapter": "database_client",
                "database": record.get("database"),
                "service": "postgresql",
                "connection_evidence": True,
                "data_collection_asserted": False,
            },
        )


class LinuxAuthAdapter:
    kind = "linux_auth"

    def parse(self, record: Mapping[str, Any]) -> SecurityEventCreate:
        message = str(record["message"])
        match = SSH_PATTERN.search(message)
        if match is None:
            raise ValueError("unsupported ssh authentication record")
        accepted = match.group("result") == "Accepted"
        return event(
            timestamp=timestamp(record.get("timestamp")),
            event_type="authentication",
            source="linux_auth",
            source_ip=match.group("source_ip"),
            destination_ip=record.get("destination_ip"),
            source_port=int(match.group("source_port")),
            destination_port=22,
            hostname=record.get("hostname"),
            username=match.group("username"),
            process_name="sshd",
            action="ssh_login",
            status="success" if accepted else "failed",
            severity="informational" if accepted else "low",
            raw_event=redact(record),
            normalized_data={
                "adapter": "linux_auth",
                "authentication_method": match.group("method"),
                "service": "ssh",
            },
        )


class SudoAdapter:
    kind = "sudo_execution"

    def parse(self, record: Mapping[str, Any]) -> SecurityEventCreate:
        return_code = int(record["return_code"])
        return event(
            timestamp=timestamp(record.get("timestamp")),
            event_type="privilege",
            source="linux_privilege",
            source_ip=record.get("source_ip"),
            hostname=record.get("hostname"),
            username=record.get("username"),
            process_name="sudo",
            action="sudo_command",
            status="success" if return_code == 0 else "failed",
            severity="medium" if return_code == 0 else "low",
            raw_event=redact(record),
            normalized_data={
                "adapter": "sudo",
                "target_user": record.get("target_user", "root"),
                "privileged": return_code == 0,
                "return_code": return_code,
            },
        )


class ServiceHealthAdapter:
    kind = "container_health"

    def parse(self, record: Mapping[str, Any]) -> SecurityEventCreate:
        return event(
            timestamp=timestamp(record.get("timestamp")),
            event_type="service_status",
            source="container_health",
            source_ip=record.get("source_ip"),
            hostname=record.get("hostname"),
            process_name=record.get("process_name", "lab-agent"),
            action="heartbeat",
            status="success",
            severity="informational",
            raw_event=redact(record),
            normalized_data={"adapter": "container_health", "state": "running"},
        )
