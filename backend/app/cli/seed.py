import argparse
import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, select

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import async_session_factory, close_database
from app.lab.assets import LAB_ASSETS as DEMO_ASSETS
from app.lab.assets import stable_id
from app.models.asset import Asset
from app.models.enums import EventSeverity
from app.models.security_event import SecurityEvent

logger = logging.getLogger(__name__)


def event_template(index: int) -> dict[str, Any]:
    templates: list[dict[str, Any]] = [
        {
            "asset": "web-server",
            "event_type": "http_request",
            "source": "web_access",
            "source_ip": f"10.10.50.{20 + index % 15}",
            "destination_ip": "10.10.10.10",
            "source_port": 41000 + index,
            "destination_port": 443,
            "username": None,
            "process_name": "nginx",
            "action": "http_get",
            "status": "success",
            "severity": EventSeverity.INFORMATIONAL,
            "raw_event": {"method": "GET", "path": "/portal", "status_code": 200},
            "normalized_data": {"protocol": "https", "http_method": "GET"},
        },
        {
            "asset": "employee-01",
            "event_type": "process_execution",
            "source": "linux_audit",
            "source_ip": None,
            "destination_ip": None,
            "source_port": None,
            "destination_port": None,
            "username": "demo-user",
            "process_name": "/usr/bin/curl",
            "action": "process_started",
            "status": "success",
            "severity": EventSeverity.INFORMATIONAL,
            "raw_event": {"executable": "/usr/bin/curl", "parent": "/usr/bin/bash"},
            "normalized_data": {"command_category": "network_client", "interactive": True},
        },
        {
            "asset": "employee-02",
            "event_type": "authentication",
            "source": "linux_auth",
            "source_ip": "10.10.20.1",
            "destination_ip": "10.10.20.11",
            "source_port": 52000 + index,
            "destination_port": 22,
            "username": "ops-user",
            "process_name": "sshd",
            "action": "ssh_login",
            "status": "success",
            "severity": EventSeverity.LOW,
            "raw_event": {"method": "password", "result": "accepted"},
            "normalized_data": {"authentication_method": "password", "service": "ssh"},
        },
        {
            "asset": "admin-server",
            "event_type": "privilege",
            "source": "linux_audit",
            "source_ip": "10.10.20.10",
            "destination_ip": "10.10.30.10",
            "source_port": None,
            "destination_port": None,
            "username": "admin-user",
            "process_name": "sudo",
            "action": "sudo_command",
            "status": "success",
            "severity": EventSeverity.MEDIUM,
            "raw_event": {"command": "systemctl status sentinel-agent", "result": "allowed"},
            "normalized_data": {"target_user": "root", "privileged": True},
        },
        {
            "asset": "database",
            "event_type": "database_connection",
            "source": "postgresql_audit",
            "source_ip": "10.10.10.10",
            "destination_ip": "10.10.30.20",
            "source_port": 54000 + index,
            "destination_port": 5432,
            "username": "portal_app",
            "process_name": "postgres",
            "action": "database_connect",
            "status": "success",
            "severity": EventSeverity.LOW,
            "raw_event": {"database": "portal", "ssl": True, "result": "authorized"},
            "normalized_data": {"database": "portal", "client": "web-server"},
        },
        {
            "asset": "employee-01",
            "event_type": "network_connection",
            "source": "host_network",
            "source_ip": "10.10.20.10",
            "destination_ip": "10.10.30.10",
            "source_port": 45000 + index,
            "destination_port": 22,
            "username": "demo-user",
            "process_name": "ssh",
            "action": "connection_opened",
            "status": "success",
            "severity": EventSeverity.INFORMATIONAL,
            "raw_event": {"protocol": "tcp", "bytes_sent": 1240 + index},
            "normalized_data": {"direction": "outbound", "protocol": "tcp"},
        },
        {
            "asset": "web-server",
            "event_type": "authentication",
            "source": "web_auth",
            "source_ip": f"10.10.50.{40 + index % 10}",
            "destination_ip": "10.10.10.10",
            "source_port": 46000 + index,
            "destination_port": 443,
            "username": "analyst@example.test",
            "process_name": "portal-api",
            "action": "web_login",
            "status": "failed",
            "severity": EventSeverity.MEDIUM,
            "raw_event": {"endpoint": "/login", "reason": "invalid_password"},
            "normalized_data": {"authentication_method": "password", "service": "portal"},
        },
        {
            "asset": "employee-01",
            "event_type": "authentication",
            "source": "linux_auth",
            "source_ip": "10.10.50.2",
            "destination_ip": "10.10.20.10",
            "source_port": 47000 + index,
            "destination_port": 22,
            "username": "demo-user",
            "process_name": "sshd",
            "action": "ssh_login",
            "status": "failed",
            "severity": EventSeverity.LOW,
            "raw_event": {"method": "password", "reason": "authentication_failure"},
            "normalized_data": {"authentication_method": "password", "service": "ssh"},
        },
        {
            "asset": "admin-server",
            "event_type": "process_execution",
            "source": "linux_audit",
            "source_ip": None,
            "destination_ip": None,
            "source_port": None,
            "destination_port": None,
            "username": "admin-user",
            "process_name": "/usr/bin/journalctl",
            "action": "process_started",
            "status": "success",
            "severity": EventSeverity.INFORMATIONAL,
            "raw_event": {"executable": "/usr/bin/journalctl", "arguments": "--since today"},
            "normalized_data": {"command_category": "administration", "privileged": False},
        },
        {
            "asset": "employee-02",
            "event_type": "session",
            "source": "linux_auth",
            "source_ip": "10.10.20.1",
            "destination_ip": "10.10.20.11",
            "source_port": None,
            "destination_port": None,
            "username": "ops-user",
            "process_name": "systemd-logind",
            "action": "logout",
            "status": "success",
            "severity": EventSeverity.INFORMATIONAL,
            "raw_event": {"session_type": "ssh", "result": "closed"},
            "normalized_data": {"session_type": "remote", "duration_seconds": 1800 + index},
        },
    ]
    return templates[index % len(templates)]


async def seed_demo(reset: bool = False) -> tuple[int, int]:
    now = datetime.now(UTC).replace(second=0, microsecond=0)
    async with async_session_factory() as session:
        assets_by_hostname: dict[str, Asset] = {}
        for values in DEMO_ASSETS:
            existing = await session.scalar(
                select(Asset).where(Asset.hostname == values["hostname"])
            )
            timeline = {
                "first_seen": now - timedelta(days=30),
                "last_seen": now - timedelta(minutes=len(assets_by_hostname) * 2),
            }
            if existing:
                for key, value in {**values, **timeline}.items():
                    if key != "id":
                        setattr(existing, key, value)
                asset = existing
            else:
                asset = Asset(**values, **timeline)
                session.add(asset)
            assets_by_hostname[values["hostname"]] = asset

        await session.flush()
        demo_event_ids = [stable_id(f"demo-event-{index:03d}") for index in range(180)]
        if reset:
            await session.execute(delete(SecurityEvent).where(SecurityEvent.id.in_(demo_event_ids)))
            await session.flush()

        existing_event_ids = set(
            await session.scalars(
                select(SecurityEvent.id).where(SecurityEvent.id.in_(demo_event_ids))
            )
        )
        created_events = 0
        for index, event_id in enumerate(demo_event_ids):
            if event_id in existing_event_ids:
                continue
            template = event_template(index)
            hostname = template["asset"]
            payload = {key: value for key, value in template.items() if key != "asset"}
            payload["normalized_data"] = {
                **payload["normalized_data"],
                "demo_seed": True,
                "origin": "synthetic",
                "sequence": index,
            }
            session.add(
                SecurityEvent(
                    id=event_id,
                    timestamp=now - timedelta(minutes=(179 - index) * 24),
                    hostname=hostname,
                    asset_id=assets_by_hostname[hostname].id,
                    **payload,
                )
            )
            created_events += 1

        await session.commit()
        logger.info(
            "Demo seed complete: %s assets synchronized, %s events created",
            len(assets_by_hostname),
            created_events,
        )
        return len(assets_by_hostname), created_events


async def run(reset: bool) -> None:
    try:
        await seed_demo(reset=reset)
    finally:
        await close_database()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed deterministic SENTINEL demo data")
    parser.add_argument(
        "--reset", action="store_true", help="Replace only the deterministic demo events"
    )
    args = parser.parse_args()
    configure_logging(get_settings().log_level)
    asyncio.run(run(reset=args.reset))


if __name__ == "__main__":
    main()
