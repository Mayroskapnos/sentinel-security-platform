"""Generate safe synthetic development telemetry for SENTINEL Milestone 2."""

from __future__ import annotations

import argparse
import http.client
import json
import os
import time
from collections.abc import Iterator
from datetime import UTC, datetime
from itertools import cycle
from typing import Any
from urllib.parse import urlparse

EVENT_TEMPLATES: tuple[dict[str, Any], ...] = (
    {
        "event_type": "authentication",
        "source": "linux_auth",
        "source_ip": "10.10.20.10",
        "destination_ip": "10.10.30.10",
        "destination_port": 22,
        "hostname": "employee-01",
        "username": "demo-user",
        "process_name": "sshd",
        "action": "ssh_login",
        "status": "success",
        "severity": "informational",
        "normalized_data": {"authentication_method": "password", "service": "ssh"},
        "raw_event": {"message": "Accepted password for demo-user"},
    },
    {
        "event_type": "http_request",
        "source": "web_access",
        "source_ip": "10.10.20.11",
        "destination_ip": "10.10.10.10",
        "destination_port": 443,
        "hostname": "web-server",
        "username": "application-user",
        "process_name": "nginx",
        "action": "get_profile",
        "status": "success",
        "severity": "informational",
        "normalized_data": {"method": "GET", "path": "/api/profile", "protocol": "HTTP/2"},
        "raw_event": {"message": "GET /api/profile 200"},
    },
    {
        "event_type": "authentication",
        "source": "linux_auth",
        "source_ip": "10.10.20.11",
        "destination_ip": "10.10.30.10",
        "destination_port": 22,
        "hostname": "employee-02",
        "username": "demo-user",
        "process_name": "sshd",
        "action": "ssh_login",
        "status": "failed",
        "severity": "low",
        "normalized_data": {"authentication_method": "password", "service": "ssh"},
        "raw_event": {"message": "Failed password for demo-user"},
    },
    {
        "event_type": "process_execution",
        "source": "linux_process",
        "source_ip": "10.10.30.10",
        "destination_ip": None,
        "hostname": "admin-server",
        "username": "administrator",
        "process_name": "systemctl",
        "action": "service_status",
        "status": "success",
        "severity": "informational",
        "normalized_data": {"command": "systemctl status nginx"},
        "raw_event": {"message": "systemctl status nginx completed"},
    },
    {
        "event_type": "database_connection",
        "source": "database",
        "source_ip": "10.10.10.10",
        "destination_ip": "10.10.30.20",
        "destination_port": 5432,
        "hostname": "database",
        "username": "application_user",
        "process_name": "postgres",
        "action": "database_connect",
        "status": "success",
        "severity": "informational",
        "normalized_data": {"database": "application", "protocol": "postgresql"},
        "raw_event": {"message": "Application database connection accepted"},
    },
    {
        "event_type": "network_connection",
        "source": "network",
        "source_ip": "10.10.20.10",
        "destination_ip": "10.10.10.10",
        "destination_port": 443,
        "hostname": "employee-01",
        "username": "demo-user",
        "process_name": "browser",
        "action": "connect",
        "status": "success",
        "severity": "informational",
        "normalized_data": {"transport": "tcp", "service": "https"},
        "raw_event": {"message": "TCP connection established"},
    },
)


class TelemetryClient:
    def __init__(self, target: str) -> None:
        parsed = urlparse(target)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("target must be an explicit http:// or https:// SENTINEL URL")
        if parsed.query or parsed.fragment:
            raise ValueError("target URL must not contain a query string or fragment")
        self.scheme = parsed.scheme
        self.host = parsed.hostname
        self.port = parsed.port
        self.base_path = parsed.path.rstrip("/")
        self.connection: http.client.HTTPConnection | None = None

    def _connect(self) -> http.client.HTTPConnection:
        connection_class = (
            http.client.HTTPSConnection if self.scheme == "https" else http.client.HTTPConnection
        )
        self.connection = connection_class(self.host, self.port, timeout=10)
        return self.connection

    def send(self, event: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(event, separators=(",", ":")).encode("utf-8")
        endpoint = f"{self.base_path}/api/v1/telemetry/events"
        for attempt in range(2):
            connection = self.connection or self._connect()
            try:
                connection.request(
                    "POST",
                    endpoint,
                    body=body,
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        "Content-Length": str(len(body)),
                    },
                )
                response = connection.getresponse()
                response_body = response.read()
                if response.status != 201:
                    detail = response_body.decode("utf-8", errors="replace")[:300]
                    raise RuntimeError(f"ingestion returned HTTP {response.status}: {detail}")
                parsed: Any = json.loads(response_body)
                if not isinstance(parsed, dict) or not isinstance(parsed.get("id"), str):
                    raise RuntimeError("ingestion response did not contain a database event ID")
                return parsed
            except (ConnectionError, http.client.HTTPException):
                self.close()
                if attempt == 1:
                    raise
        raise RuntimeError("telemetry request failed")

    def close(self) -> None:
        if self.connection:
            self.connection.close()
            self.connection = None


def generated_events() -> Iterator[dict[str, Any]]:
    for template in cycle(EVENT_TEMPLATES):
        event = dict(template)
        event["timestamp"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        event["normalized_data"] = dict(template["normalized_data"])
        event["raw_event"] = dict(template["raw_event"])
        yield event


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send safe synthetic development telemetry to SENTINEL."
    )
    parser.add_argument(
        "--target",
        default=os.getenv("SENTINEL_URL", "http://localhost:8000"),
        help="Explicit SENTINEL base URL (default: %(default)s)",
    )
    parser.add_argument("--mode", choices=("single", "stream", "burst"), default="single")
    parser.add_argument("--count", type=int, help="Number of events (stream: 25, burst: 100)")
    parser.add_argument("--interval", type=float, help="Seconds between stream events (default: 2)")
    args = parser.parse_args()
    default_count = {"single": 1, "stream": 25, "burst": 100}[args.mode]
    args.count = default_count if args.count is None else args.count
    args.interval = (
        (2.0 if args.mode == "stream" else 0.02) if args.interval is None else args.interval
    )
    if not 1 <= args.count <= 1_000:
        parser.error("--count must be between 1 and 1000")
    if args.interval < 0:
        parser.error("--interval must be zero or greater")
    if args.mode == "single":
        args.count = 1
    return args


def main() -> int:
    args = parse_args()
    client = TelemetryClient(args.target)
    interval = 0.0 if args.mode == "single" else args.interval
    print("SENTINEL Synthetic Telemetry Producer")
    print(f"Target: {args.target}")
    print(f"Mode: {args.mode} | Count: {args.count} | Interval: {interval:g}s")
    sent = 0
    try:
        for event in generated_events():
            response = client.send(event)
            sent += 1
            print(
                f"[{sent:03d}] {event['hostname']} {event['event_type']} "
                f"{event['action']} {event['status']} id={response['id']}"
            )
            if sent >= args.count:
                break
            if interval:
                time.sleep(interval)
    except KeyboardInterrupt:
        print("\nProducer stopped by user.")
    finally:
        client.close()
        print(f"Producer shutdown. Events sent: {sent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
