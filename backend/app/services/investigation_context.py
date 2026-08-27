import hashlib
import json
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.investigation.redaction import bounded_redacted_json, redact_value
from app.models.alert import AlertEvent
from app.models.incident import IncidentAlert
from app.models.network_connection import NetworkConnection
from app.models.security_event import SecurityEvent
from app.repositories.incidents import IncidentRepository
from app.schemas.investigation import InvestigationContext
from app.services.incidents import IncidentService


def evidence_ref(kind: str, identifier: UUID) -> str:
    return f"{kind}:{identifier}"


class InvestigationContextBuilder:
    """Build one bounded, redacted package from authoritative Incident evidence."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = IncidentRepository(session)

    async def build(self, incident_id: UUID) -> tuple[InvestigationContext, str]:
        incident = await self.repository.get(incident_id)
        if incident is None:
            from app.core.errors import NotFoundError

            raise NotFoundError("INCIDENT_NOT_FOUND", "Requested incident does not exist.")
        detail = IncidentService.detail(incident)
        event_rows = await self._evidence_rows(incident_id)
        selected_events = self._select_key_events(event_rows)
        selected_event_ids = {event.id for event in selected_events}
        connections = await self._network_relationships(detail)
        catalog = self._evidence_catalog(detail, selected_events, connections)

        context = InvestigationContext(
            incident={
                "ref": evidence_ref("incident", detail.id),
                "incident_number": detail.incident_number,
                "title": detail.title,
                "severity": detail.severity,
                "status": detail.status,
                "confidence_score": detail.confidence_score,
                "risk_score": detail.risk_score,
                "first_activity_at": detail.first_activity_at,
                "last_activity_at": detail.last_activity_at,
                "alert_count": detail.alert_count,
                "asset_count": detail.asset_count,
                "event_count": detail.event_count,
                "summary": detail.summary,
            },
            assets=[
                {
                    "ref": evidence_ref("asset", asset.id),
                    "hostname": asset.hostname,
                    "display_name": asset.display_name,
                    "ip_address": asset.ip_address,
                    "asset_type": asset.asset_type,
                    "network_zone": asset.network_zone,
                    "criticality": asset.criticality,
                    "status": asset.status,
                    "risk_score": asset.risk_score,
                }
                for asset in detail.assets
            ],
            alerts=[
                {
                    "ref": evidence_ref("alert", alert.id),
                    "rule_id": alert.rule_id,
                    "title": alert.title,
                    "severity": alert.severity,
                    "status": alert.status,
                    "first_event_at": alert.first_event_at,
                    "last_event_at": alert.last_event_at,
                    "asset_ref": (
                        evidence_ref("asset", alert.asset_id) if alert.asset_id else None
                    ),
                    "asset_hostname": alert.asset_hostname,
                    "evidence_count": alert.evidence_count,
                    "correlation_score": alert.correlation_score,
                    "correlation_reasons": [
                        reason.model_dump(mode="json") for reason in alert.correlation_reasons
                    ],
                }
                for alert in detail.alerts
            ],
            deterministic_story=[
                {
                    "timestamp": item.timestamp,
                    "stage": item.stage,
                    "title": item.title,
                    "description": item.description,
                    "alert_ref": evidence_ref("alert", item.alert_id),
                    "asset_refs": [evidence_ref("asset", item_id) for item_id in item.asset_ids],
                    "event_refs": [
                        evidence_ref("event", item_id)
                        for item_id in item.event_ids
                        if item_id in selected_event_ids
                    ],
                    "source_ip": item.source_ip,
                    "destination_ip": item.destination_ip,
                    "network_connection_ref": (
                        evidence_ref("connection", item.network_connection_id)
                        if item.network_connection_id
                        else None
                    ),
                }
                for item in detail.story
            ],
            observed_attack_techniques=[
                {
                    "technique_id": technique.technique_id,
                    "technique_name": technique.technique_name,
                    "tactic": technique.tactic,
                    "first_observed_at": technique.first_observed_at,
                    "alert_refs": [
                        evidence_ref("alert", alert_id) for alert_id in technique.alert_ids
                    ],
                }
                for technique in detail.observed_techniques
            ],
            correlation_evidence=[
                redact_value(signal.model_dump(mode="json"))
                for signal in detail.correlation_signals
            ],
            network_relationships=[
                {
                    "ref": evidence_ref("connection", connection.id),
                    "source_asset_ref": evidence_ref("asset", connection.source_asset_id),
                    "destination_asset_ref": evidence_ref("asset", connection.destination_asset_id),
                    "source_ip": connection.source_ip,
                    "destination_ip": connection.destination_ip,
                    "destination_port": connection.destination_port,
                    "protocol": connection.protocol,
                    "connection_type": connection.connection_type,
                }
                for connection in connections
            ],
            key_events=[self._event_context(event) for event in selected_events],
            scenario_context=(
                {
                    "ref": evidence_ref("scenario", detail.scenario.id),
                    "scenario_id": detail.scenario.scenario_id,
                    "scenario_name": detail.scenario.scenario_name,
                    "status": detail.scenario.status,
                }
                if detail.scenario
                else None
            ),
            evidence_catalog=catalog,
        )
        hash_payload = context.model_dump(mode="json")
        # Workflow and global Asset posture are useful provider context but do not
        # represent a change to this Incident's evidence version.
        hash_payload["incident"].pop("status", None)
        for asset in hash_payload["assets"]:
            asset.pop("status", None)
            asset.pop("risk_score", None)
        serialized = json.dumps(
            hash_payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        return context, hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    async def _evidence_rows(self, incident_id: UUID) -> list[tuple[UUID, SecurityEvent]]:
        query_limit = min(2_500, self.settings.sentinel_ai_max_context_events * 20)
        rows = list(
            await self.session.execute(
                select(AlertEvent.alert_id, SecurityEvent)
                .join(SecurityEvent, SecurityEvent.id == AlertEvent.event_id)
                .join(IncidentAlert, IncidentAlert.alert_id == AlertEvent.alert_id)
                .where(IncidentAlert.incident_id == incident_id)
                .order_by(SecurityEvent.timestamp, SecurityEvent.id)
                .limit(query_limit)
            )
        )
        unique: dict[UUID, tuple[UUID, SecurityEvent]] = {}
        for alert_id, event in rows:
            unique.setdefault(event.id, (alert_id, event))
        return list(unique.values())

    def _select_key_events(self, rows: list[tuple[UUID, SecurityEvent]]) -> list[SecurityEvent]:
        by_alert: dict[UUID, list[SecurityEvent]] = defaultdict(list)
        for alert_id, event in rows:
            by_alert[alert_id].append(event)
        ranked: dict[UUID, tuple[int, SecurityEvent]] = {}

        def include(event: SecurityEvent, priority: int) -> None:
            previous = ranked.get(event.id)
            if previous is None or priority > previous[0]:
                ranked[event.id] = (priority, event)

        for events in by_alert.values():
            include(events[0], 20)
            include(events[-1], 20)
        for _, event in rows:
            if event.event_type in {
                "database_connection",
                "database_query",
                "network_connection",
                "privilege",
            } or (event.event_type == "authentication" and event.status == "success"):
                include(event, 30)
            else:
                include(event, 10)
        candidates = sorted(
            ranked.values(),
            key=lambda item: (-item[0], self._as_utc(item[1].timestamp), str(item[1].id)),
        )[: self.settings.sentinel_ai_max_context_events]
        return sorted(
            (item[1] for item in candidates),
            key=lambda event: (self._as_utc(event.timestamp), str(event.id)),
        )

    async def _network_relationships(self, detail) -> list[NetworkConnection]:  # noqa: ANN001
        story_connection_ids = {
            item.network_connection_id for item in detail.story if item.network_connection_id
        }
        if not story_connection_ids:
            return []
        query = (
            select(NetworkConnection)
            .where(NetworkConnection.id.in_(story_connection_ids))
            .order_by(NetworkConnection.last_seen.desc(), NetworkConnection.id)
            .limit(self.settings.sentinel_ai_max_network_relationships)
        )
        return list(await self.session.scalars(query))

    @staticmethod
    def _evidence_catalog(detail, events, connections) -> dict[str, str]:  # noqa: ANN001
        catalog = {evidence_ref("incident", detail.id): detail.incident_number}
        catalog.update({evidence_ref("asset", asset.id): asset.hostname for asset in detail.assets})
        catalog.update({evidence_ref("alert", alert.id): alert.rule_id for alert in detail.alerts})
        catalog.update(
            {
                evidence_ref("event", event.id): f"{event.event_type} {str(event.id)[:8]}"
                for event in events
            }
        )
        catalog.update(
            {
                evidence_ref("connection", connection.id): (
                    f"{connection.source_ip} to {connection.destination_ip}"
                    + (
                        f":{connection.destination_port}"
                        if connection.destination_port is not None
                        else ""
                    )
                )
                for connection in connections
            }
        )
        if detail.scenario:
            catalog[evidence_ref("scenario", detail.scenario.id)] = detail.scenario.scenario_id
        return dict(sorted(catalog.items()))

    @staticmethod
    def _event_context(event: SecurityEvent) -> dict[str, Any]:
        return {
            "ref": evidence_ref("event", event.id),
            "timestamp": event.timestamp,
            "event_type": event.event_type,
            "source": event.source,
            "source_ip": event.source_ip,
            "destination_ip": event.destination_ip,
            "source_port": event.source_port,
            "destination_port": event.destination_port,
            "hostname": event.hostname,
            "username": event.username,
            "process_name": event.process_name,
            "action": event.action,
            "status": event.status,
            "severity": event.severity,
            "asset_ref": evidence_ref("asset", event.asset_id) if event.asset_id else None,
            "scenario_ref": (
                evidence_ref("scenario", event.scenario_run_id) if event.scenario_run_id else None
            ),
            "raw_excerpt_untrusted": bounded_redacted_json(event.raw_event),
            "normalized_excerpt_untrusted": bounded_redacted_json(event.normalized_data),
        }

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
