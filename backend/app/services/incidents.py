from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.correlation.story_templates import (
    STORY_TEMPLATES,
    incident_title,
    stage_summary,
    story_description,
)
from app.models.alert import Alert, AlertEvent
from app.models.asset import Asset
from app.models.enums import AlertStatus, IncidentStatus
from app.models.incident import Incident, IncidentAlert, IncidentAsset
from app.models.network_connection import NetworkConnection
from app.models.security_event import SecurityEvent
from app.repositories.incidents import IncidentRepository
from app.schemas.common import Page
from app.schemas.incident import (
    CorrelationSignal,
    IncidentAlertReference,
    IncidentAssetReference,
    IncidentDetail,
    IncidentFilters,
    IncidentListItem,
    IncidentScenarioReference,
    IncidentStoryItem,
    IncidentTechnique,
    IncidentUpdate,
)
from app.services.network import NetworkService

ACTIVE_ALERT_STATUSES = {AlertStatus.NEW, AlertStatus.INVESTIGATING}
SEVERITY_BASE = {
    "informational": 10,
    "low": 20,
    "medium": 40,
    "high": 65,
    "critical": 85,
}
CRITICALITY_MODIFIER = {"low": 0, "medium": 3, "high": 7, "critical": 10}
ALLOWED_TRANSITIONS = {
    IncidentStatus.OPEN: {
        IncidentStatus.INVESTIGATING,
        IncidentStatus.RESOLVED,
        IncidentStatus.FALSE_POSITIVE,
    },
    IncidentStatus.INVESTIGATING: {
        IncidentStatus.CONTAINED,
        IncidentStatus.RESOLVED,
        IncidentStatus.FALSE_POSITIVE,
    },
    IncidentStatus.CONTAINED: {IncidentStatus.INVESTIGATING, IncidentStatus.RESOLVED},
    IncidentStatus.RESOLVED: {IncidentStatus.INVESTIGATING},
    IncidentStatus.FALSE_POSITIVE: {IncidentStatus.INVESTIGATING},
}


class IncidentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = IncidentRepository(session)

    async def list(self, filters: IncidentFilters) -> Page[IncidentListItem]:
        incidents, total = await self.repository.list(filters)
        return Page[IncidentListItem].create(
            items=[self.list_item(incident) for incident in incidents],
            page=filters.page,
            page_size=filters.page_size,
            total=total,
        )

    async def get(self, incident_id: UUID) -> IncidentDetail:
        incident = await self.repository.get(incident_id)
        if incident is None:
            raise NotFoundError("INCIDENT_NOT_FOUND", "Requested incident does not exist.")
        return self.detail(incident)

    async def update(self, incident_id: UUID, payload: IncidentUpdate) -> IncidentDetail:
        incident = await self.repository.get(incident_id)
        if incident is None:
            raise NotFoundError("INCIDENT_NOT_FOUND", "Requested incident does not exist.")
        if payload.status is not None and payload.status != incident.status:
            current = IncidentStatus(incident.status)
            if payload.status not in ALLOWED_TRANSITIONS[current]:
                raise ConflictError(
                    "INVALID_INCIDENT_STATUS_TRANSITION",
                    f"Incident cannot move from {current.value} to {payload.status.value}.",
                )
            incident.status = payload.status
            incident.closed_at = (
                datetime.now(UTC)
                if payload.status in {IncidentStatus.RESOLVED, IncidentStatus.FALSE_POSITIVE}
                else None
            )
        if "assigned_to" in payload.model_fields_set:
            incident.assigned_to = payload.assigned_to.strip() if payload.assigned_to else None
        await self.session.commit()
        refreshed = await self.repository.get(incident_id)
        assert refreshed is not None
        return self.detail(refreshed)

    async def recalculate(self, incident_id: UUID) -> IncidentDetail:
        incident = await self.repository.get(incident_id)
        if incident is None:
            raise NotFoundError("INCIDENT_NOT_FOUND", "Requested incident does not exist.")
        await self.recalculate_model(incident)
        await self.session.commit()
        refreshed = await self.repository.get(incident_id)
        assert refreshed is not None
        return self.detail(refreshed)

    async def recalculate_model(self, incident: Incident) -> None:
        await self.session.flush()
        incident = await self.repository.get(incident.id) or incident
        links = sorted(
            incident.alert_links,
            key=lambda link: (self._as_utc(link.alert.first_event_at), str(link.alert.id)),
        )
        alerts = [link.alert for link in links]
        evidence_rows = list(
            await self.session.execute(
                select(AlertEvent.alert_id, SecurityEvent)
                .join(SecurityEvent, SecurityEvent.id == AlertEvent.event_id)
                .join(IncidentAlert, IncidentAlert.alert_id == AlertEvent.alert_id)
                .where(IncidentAlert.incident_id == incident.id)
                .order_by(SecurityEvent.timestamp, SecurityEvent.id)
            )
        )
        events_by_alert: dict[UUID, list[SecurityEvent]] = defaultdict(list)
        for alert_id, event in evidence_rows:
            events_by_alert[alert_id].append(event)
        distinct_events = {event.id: event for _, event in evidence_rows}

        all_assets = list(await self.session.scalars(select(Asset).order_by(Asset.hostname)))
        assets_by_id = {asset.id: asset for asset in all_assets}
        assets_by_ip = NetworkService._assets_by_ip(all_assets)
        affected_ids: set[UUID] = set()
        scenario_ids: set[UUID] = set()
        for alert in alerts:
            if alert.asset_id:
                affected_ids.add(alert.asset_id)
            for event in events_by_alert[alert.id]:
                if event.asset_id:
                    affected_ids.add(event.asset_id)
                if event.scenario_run_id:
                    scenario_ids.add(event.scenario_run_id)
                for ip_address in (event.source_ip, event.destination_ip):
                    asset = assets_by_ip.get(ip_address or "")
                    if asset:
                        affected_ids.add(asset.id)

        existing_asset_ids = {link.asset_id for link in incident.asset_links}
        removed_ids = existing_asset_ids - affected_ids
        if removed_ids:
            incident.asset_links[:] = [
                link for link in incident.asset_links if link.asset_id not in removed_ids
            ]
        for asset_id in sorted(affected_ids - existing_asset_ids, key=str):
            incident.asset_links.append(
                IncidentAsset(
                    incident_id=incident.id,
                    asset_id=asset_id,
                    asset=assets_by_id[asset_id],
                )
            )

        effective_alerts = [alert for alert in alerts if alert.status != AlertStatus.FALSE_POSITIVE]
        active_alerts = [
            alert for alert in effective_alerts if alert.status in ACTIVE_ALERT_STATUSES
        ]
        stages = {
            STORY_TEMPLATES[alert.detection_rule.rule_id].stage
            for alert in effective_alerts
            if alert.detection_rule.rule_id in STORY_TEMPLATES
        }
        risk, components = self._risk_score(
            active_alerts, effective_alerts, affected_ids, stages, assets_by_id
        )
        incident.risk_score = risk
        incident.severity = self._severity(risk)
        if not effective_alerts:
            incident.status = IncidentStatus.FALSE_POSITIVE
            incident.closed_at = incident.closed_at or datetime.now(UTC)

        association_scores = [
            link.correlation_score
            for link in links
            if not any(
                reason.get("type") == "incident_created"
                for reason in link.correlation_reasons
                if isinstance(reason, dict)
            )
        ]
        incident.confidence_score = (
            round(sum(association_scores) / len(association_scores)) if association_scores else 25
        )
        incident.first_activity_at = min(self._as_utc(alert.first_event_at) for alert in alerts)
        incident.last_activity_at = max(self._as_utc(alert.last_event_at) for alert in alerts)
        incident.scenario_run_id = next(iter(scenario_ids)) if len(scenario_ids) == 1 else None

        story = await self._build_story(
            effective_alerts, events_by_alert, assets_by_id, assets_by_ip
        )
        ordered_stages = list(dict.fromkeys(item.stage for item in story))
        incident.title = incident_title(set(ordered_stages))
        incident.description = (
            f"SENTINEL deterministically correlated {len(alerts)} alerts using persisted "
            "identity, asset, network, timing, progression, and scenario evidence where present."
        )
        duration = max(
            0,
            round(
                (
                    self._as_utc(incident.last_activity_at)
                    - self._as_utc(incident.first_activity_at)
                ).total_seconds()
            ),
        )
        incident.summary = (
            f"SENTINEL correlated {len(alerts)} alerts involving {len(affected_ids)} assets "
            f"over {duration} seconds. The observed activity included "
            f"{stage_summary(ordered_stages)}."
        )
        incident.story = [item.model_dump(mode="json") for item in story]
        incident.correlation_reasons = self._aggregate_reasons(links)
        incident.metadata_json = {
            "engine_version": "1",
            "confidence_label": self.confidence_label(incident.confidence_score),
            "experimental_deterministic_confidence": True,
            "event_count": len(distinct_events),
            "alert_count": len(alerts),
            "asset_count": len(affected_ids),
            "observed_stages": ordered_stages,
            "risk_formula": components,
            "evidence_truncated": len(evidence_rows) >= 2_500,
        }
        await self.session.flush()

    async def _build_story(
        self,
        alerts: list[Alert],
        events_by_alert: dict[UUID, list[SecurityEvent]],
        assets_by_id: dict[UUID, Asset],
        assets_by_ip: dict[str, Asset],
    ) -> list[IncidentStoryItem]:
        observations: dict[UUID, tuple[str, set[UUID]]] = {}
        relationship_keys: set[str] = set()
        for alert in alerts:
            keys: set[str] = set()
            for event in events_by_alert[alert.id]:
                observation = NetworkService.observation_for(event, assets_by_ip)
                if observation:
                    keys.add(observation.key)
                    relationship_keys.add(observation.key)
            if keys:
                observations[alert.id] = (sorted(keys)[0], set())
        connection_ids = {
            item.relationship_key: item.id
            for item in await self.session.scalars(
                select(NetworkConnection).where(
                    NetworkConnection.relationship_key.in_(relationship_keys)
                )
            )
        }

        story: list[IncidentStoryItem] = []
        for alert in sorted(
            alerts, key=lambda item: (self._as_utc(item.first_event_at), str(item.id))
        ):
            rule_id = alert.detection_rule.rule_id
            template = STORY_TEMPLATES.get(rule_id)
            stage = template.stage if template else "alert_activity"
            title = template.title if template else alert.title
            evidence = events_by_alert[alert.id]
            asset_ids = {alert.asset_id} if alert.asset_id else set()
            for event in evidence:
                if event.asset_id:
                    asset_ids.add(event.asset_id)
                for ip_address in (event.source_ip, event.destination_ip):
                    asset = assets_by_ip.get(ip_address or "")
                    if asset:
                        asset_ids.add(asset.id)
            asset_hostname = (
                alert.asset.hostname
                if alert.asset
                else next(
                    (
                        assets_by_id[asset_id].hostname
                        for asset_id in asset_ids
                        if asset_id in assets_by_id
                    ),
                    None,
                )
            )
            relationship_key = observations.get(alert.id, (None, set()))[0]
            story.append(
                IncidentStoryItem(
                    timestamp=alert.first_event_at,
                    stage=stage,
                    title=title,
                    description=story_description(
                        rule_id,
                        evidence_count=len(evidence),
                        asset_hostname=asset_hostname,
                        username=alert.username,
                        source_ip=alert.source_ip,
                        destination_ip=alert.destination_ip,
                    ),
                    alert_id=alert.id,
                    rule_id=rule_id,
                    asset_ids=sorted(asset_ids, key=str),
                    event_ids=[event.id for event in evidence],
                    source_ip=alert.source_ip,
                    destination_ip=alert.destination_ip,
                    mitre_technique_id=alert.mitre_technique_id,
                    mitre_technique_name=alert.mitre_technique_name,
                    network_connection_id=(
                        connection_ids.get(relationship_key) if relationship_key else None
                    ),
                )
            )
        return story

    @staticmethod
    def _risk_score(
        active_alerts: list[Alert],
        effective_alerts: list[Alert],
        affected_ids: set[UUID],
        stages: set[str],
        assets_by_id: dict[UUID, Asset],
    ) -> tuple[float, dict[str, float | int]]:
        if not effective_alerts:
            return 0.0, {
                "base_alert_severity": 0,
                "active_alert_modifier": 0,
                "asset_criticality_modifier": 0,
                "affected_asset_modifier": 0,
                "privileged_activity_modifier": 0,
                "database_access_modifier": 0,
            }
        severity_source = active_alerts or effective_alerts
        base = max(SEVERITY_BASE[alert.severity] for alert in severity_source)
        if not active_alerts:
            base = round(base * 0.5)
        active_modifier = min(15, max(0, len(active_alerts) - 1) * 4)
        criticality_modifier = max(
            (CRITICALITY_MODIFIER[assets_by_id[item].criticality] for item in affected_ids),
            default=0,
        )
        asset_modifier = min(10, max(0, len(affected_ids) - 1) * 3)
        privilege_modifier = 8 if "privilege_activity" in stages else 0
        database_modifier = 5 if "database_access" in stages else 0
        components = {
            "base_alert_severity": base,
            "active_alert_modifier": active_modifier,
            "asset_criticality_modifier": criticality_modifier,
            "affected_asset_modifier": asset_modifier,
            "privileged_activity_modifier": privilege_modifier,
            "database_access_modifier": database_modifier,
        }
        return float(min(100, sum(components.values()))), components

    @staticmethod
    def _severity(risk_score: float) -> str:
        if risk_score >= 80:
            return "critical"
        if risk_score >= 60:
            return "high"
        if risk_score >= 40:
            return "medium"
        if risk_score >= 20:
            return "low"
        return "informational"

    @staticmethod
    def confidence_label(score: int) -> str:
        if score >= 80:
            return "high"
        if score >= 50:
            return "moderate"
        return "low"

    @staticmethod
    def _aggregate_reasons(links: list[IncidentAlert]) -> list[dict]:
        reasons: list[dict] = []
        for link in links:
            for reason in link.correlation_reasons:
                if isinstance(reason, dict) and reason.get("type") != "incident_created":
                    reasons.append({**reason, "alert_id": str(link.alert_id)})
        return reasons

    @staticmethod
    def list_item(incident: Incident) -> IncidentListItem:
        metadata = incident.metadata_json or {}
        return IncidentListItem(
            id=incident.id,
            incident_number=incident.incident_number,
            title=incident.title,
            severity=incident.severity,
            status=incident.status,
            confidence_score=incident.confidence_score,
            risk_score=incident.risk_score,
            first_activity_at=incident.first_activity_at,
            last_activity_at=incident.last_activity_at,
            created_at=incident.created_at,
            updated_at=incident.updated_at,
            alert_count=len(incident.alert_links),
            asset_count=len(incident.asset_links),
            event_count=int(metadata.get("event_count", 0)),
            affected_assets=sorted(link.asset.hostname for link in incident.asset_links),
            scenario_run_id=incident.scenario_run_id,
        )

    @classmethod
    def detail(cls, incident: Incident) -> IncidentDetail:
        base = cls.list_item(incident)
        alerts = [
            IncidentAlertReference(
                id=link.alert.id,
                rule_id=link.alert.detection_rule.rule_id,
                title=link.alert.title,
                severity=link.alert.severity,
                status=link.alert.status,
                timestamp=link.alert.timestamp,
                first_event_at=link.alert.first_event_at,
                last_event_at=link.alert.last_event_at,
                asset_id=link.alert.asset_id,
                asset_hostname=link.alert.asset.hostname if link.alert.asset else None,
                evidence_count=link.alert.evidence_count,
                correlation_score=link.correlation_score,
                correlation_reasons=[
                    CorrelationSignal.model_validate(reason)
                    for reason in link.correlation_reasons
                    if reason.get("type") != "incident_created"
                ],
            )
            for link in sorted(
                incident.alert_links,
                key=lambda item: (cls._as_utc(item.alert.first_event_at), str(item.alert_id)),
            )
        ]
        techniques: dict[tuple[str, str, str], tuple[datetime, list[UUID]]] = {}
        for link in sorted(
            incident.alert_links,
            key=lambda item: (cls._as_utc(item.alert.first_event_at), str(item.alert_id)),
        ):
            alert = link.alert
            if (
                alert.status == AlertStatus.FALSE_POSITIVE
                or not alert.mitre_technique_id
                or not alert.mitre_technique_name
                or not alert.mitre_tactic
            ):
                continue
            key = (alert.mitre_technique_id, alert.mitre_technique_name, alert.mitre_tactic)
            observed_at, ids = techniques.get(key, (alert.first_event_at, []))
            ids.append(alert.id)
            techniques[key] = (min(observed_at, alert.first_event_at), ids)
        observed_techniques = [
            IncidentTechnique(
                technique_id=key[0],
                technique_name=key[1],
                tactic=key[2],
                first_observed_at=value[0],
                alert_ids=value[1],
            )
            for key, value in sorted(techniques.items(), key=lambda item: item[1][0])
        ]
        return IncidentDetail(
            **base.model_dump(),
            description=incident.description,
            summary=incident.summary,
            closed_at=incident.closed_at,
            assigned_to=incident.assigned_to,
            correlation_signals=[
                CorrelationSignal.model_validate(reason) for reason in incident.correlation_reasons
            ],
            story=[IncidentStoryItem.model_validate(item) for item in incident.story],
            alerts=alerts,
            assets=[
                IncidentAssetReference(
                    id=link.asset.id,
                    hostname=link.asset.hostname,
                    display_name=link.asset.display_name,
                    ip_address=link.asset.ip_address,
                    asset_type=link.asset.asset_type,
                    network_zone=link.asset.network_zone,
                    criticality=link.asset.criticality,
                    status=link.asset.status,
                    risk_score=link.asset.risk_score,
                )
                for link in sorted(incident.asset_links, key=lambda item: item.asset.hostname)
            ],
            observed_techniques=observed_techniques,
            scenario=(
                IncidentScenarioReference(
                    id=incident.scenario_run.id,
                    scenario_id=incident.scenario_run.scenario_id,
                    scenario_name=incident.scenario_run.scenario_name,
                    status=incident.scenario_run.status,
                )
                if incident.scenario_run
                else None
            ),
            metadata_json=incident.metadata_json,
        )

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
