import re
from collections.abc import Mapping
from typing import Any

from app.collector.adapters.common import event, optional_int, redact, timestamp
from app.schemas.security_event import SecurityEventCreate

AUTH_FAILURE = re.compile(r'password authentication failed for user "(?P<username>[^"]+)"')


class PostgresAdapter:
    def __init__(self, source_ip_aliases: Mapping[str, str] | None = None) -> None:
        self.source_ip_aliases = dict(source_ip_aliases or {})

    def parse(self, record: Mapping[str, Any]) -> SecurityEventCreate | None:
        message = str(record.get("message", ""))
        source_ip = record.get("remote_host")
        if source_ip in (None, "[local]"):
            return None
        if isinstance(source_ip, str):
            source_ip = self.source_ip_aliases.get(source_ip, source_ip)
        common = {
            "timestamp": timestamp(record.get("timestamp")),
            "source": "postgresql",
            "source_ip": source_ip,
            "destination_ip": "10.10.30.20",
            "source_port": optional_int(record.get("remote_port")),
            "destination_port": 5432,
            "hostname": "database",
            "username": record.get("user"),
            "process_name": "postgres",
            "raw_event": redact(record),
        }
        if message.startswith("connection authorized"):
            return event(
                **common,
                event_type="database_connection",
                action="database_connect",
                status="success",
                severity="informational",
                normalized_data={
                    "adapter": "postgresql",
                    "database": record.get("dbname"),
                    "session_id": record.get("session_id"),
                    "connection_evidence": True,
                    "data_collection_asserted": False,
                },
            )
        failure = AUTH_FAILURE.search(message)
        if failure:
            return event(
                **{**common, "username": failure.group("username")},
                event_type="database_connection",
                action="database_connect",
                status="failed",
                severity="low",
                normalized_data={
                    "adapter": "postgresql",
                    "database": record.get("dbname"),
                    "session_id": record.get("session_id"),
                    "connection_evidence": True,
                    "data_collection_asserted": False,
                },
            )
        if message.startswith("disconnection:"):
            return event(
                **common,
                event_type="database_session",
                action="database_disconnect",
                status="success",
                severity="informational",
                normalized_data={
                    "adapter": "postgresql",
                    "database": record.get("dbname"),
                    "session_id": record.get("session_id"),
                },
            )
        command_tag = record.get("command_tag")
        statement_logged = " statement: " in message and message.startswith("duration:")
        query_category = command_tag or (record.get("ps") if statement_logged else None)
        if query_category:
            return event(
                **common,
                event_type="database_query",
                action="database_query",
                status="success",
                severity="informational",
                normalized_data={
                    "adapter": "postgresql",
                    "database": record.get("dbname"),
                    "session_id": record.get("session_id"),
                    "query_category": str(query_category).lower(),
                    "query_observed": True,
                },
            )
        return None
