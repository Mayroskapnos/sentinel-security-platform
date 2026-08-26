import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.correlation.config import CORRELATION_CONFIG, DETECTION_PROGRESSION
from app.models.alert import Alert
from app.models.enums import AlertStatus, IncidentStatus
from app.models.incident import Incident, IncidentAlert
from app.models.network_connection import NetworkConnection
from app.models.security_event import SecurityEvent
from app.repositories.incidents import IncidentRepository
from app.schemas.incident import CorrelationSignal, IncidentListItem
from app.services.incidents import IncidentService

logger = logging.getLogger(__name__)
correlation_lock = asyncio.Lock()


@dataclass(frozen=True)
class AlertContext:
    alert: Alert
    events: list[SecurityEvent]
    asset_ids: frozenset[UUID]
    source_ips: frozenset[str]
    usernames: frozenset[str]
    scenario_run_ids: frozenset[UUID]


@dataclass(frozen=True)
class CandidateScore:
    incident: Incident
    score: int
    signals: tuple[CorrelationSignal, ...]


@dataclass(frozen=True)
class CorrelationOutcome:
    incident: IncidentListItem
    created: bool


class CorrelationService:
    """Attach an authoritative alert to at most one explainable active incident."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = IncidentRepository(session)

    async def process_alert(self, alert_id: UUID) -> CorrelationOutcome:
        async with correlation_lock:
            alert = await self._alert(alert_id)
            if alert is None:
                raise ValueError(f"alert {alert_id} does not exist")
            existing = await self.repository.for_alert(alert_id)
            if existing:
                await IncidentService(self.session).recalculate_model(existing)
                await self.session.commit()
                refreshed = await self.repository.get(existing.id)
                assert refreshed is not None
                return CorrelationOutcome(
                    incident=IncidentService.list_item(refreshed), created=False
                )

            context = self._context(alert)
            await self._database_lock(context)
            window = timedelta(seconds=CORRELATION_CONFIG.correlation_window_seconds)
            candidates = await self.repository.candidates(
                window_start=self._as_utc(alert.first_event_at) - window,
                window_end=self._as_utc(alert.last_event_at) + window,
                limit=CORRELATION_CONFIG.candidate_limit,
            )
            relevant_asset_ids = set(context.asset_ids)
            for candidate in candidates:
                relevant_asset_ids.update(link.asset_id for link in candidate.asset_links)
            connection_rows = await self.session.execute(
                select(
                    NetworkConnection.source_asset_id,
                    NetworkConnection.destination_asset_id,
                ).where(
                    NetworkConnection.source_asset_id.in_(relevant_asset_ids),
                    NetworkConnection.destination_asset_id.in_(relevant_asset_ids),
                )
            )
            connections = {(row[0], row[1]) for row in connection_rows}
            scored = [
                self.score_candidate(context, candidate, connections)
                for candidate in candidates
                if not self._scenario_conflict(context, candidate)
            ]
            qualified = sorted(
                (item for item in scored if item.score >= CORRELATION_CONFIG.minimum_score),
                key=lambda item: (
                    -item.score,
                    -self._as_utc(item.incident.last_activity_at).timestamp(),
                    str(item.incident.id),
                ),
            )
            best = qualified[0] if qualified else None
            if len(qualified) > 1 and qualified[0].score == qualified[1].score:
                best = None

            created = best is None
            if created:
                incident_id = uuid4()
                incident = Incident(
                    id=incident_id,
                    incident_number=f"INC-{incident_id.hex[:8].upper()}",
                    title="Correlated Security Activity",
                    description="Incident created from one persisted detection alert.",
                    severity=alert.severity,
                    status=IncidentStatus.OPEN,
                    confidence_score=25,
                    risk_score=alert.risk_score,
                    first_activity_at=alert.first_event_at,
                    last_activity_at=alert.last_event_at,
                    summary="SENTINEL created this incident from one evidence-backed alert.",
                    correlation_reasons=[],
                    story=[],
                    metadata_json={},
                    alert_links=[],
                    asset_links=[],
                    scenario_run_id=(
                        next(iter(context.scenario_run_ids))
                        if len(context.scenario_run_ids) == 1
                        else None
                    ),
                )
                self.session.add(incident)
                await self.session.flush()
                score = 25
                reasons = [
                    CorrelationSignal(
                        type="incident_created",
                        weight=25,
                        strength="foundational",
                        description="This alert established the incident.",
                    )
                ]
            else:
                incident = best.incident
                score = best.score
                reasons = list(best.signals)

            link = IncidentAlert(
                incident_id=incident.id,
                alert_id=alert.id,
                correlation_score=score,
                correlation_reasons=[reason.model_dump(mode="json") for reason in reasons],
            )
            incident.alert_links.append(link)
            await IncidentService(self.session).recalculate_model(incident)
            await self.session.commit()
            refreshed = await self.repository.get(incident.id)
            assert refreshed is not None
            logger.info(
                "incident_%s incident_id=%s alert_id=%s correlation_score=%d",
                "created" if created else "updated",
                incident.id,
                alert.id,
                score,
            )
            return CorrelationOutcome(
                incident=IncidentService.list_item(refreshed), created=created
            )

    async def rebuild(self, limit: int = 5_000) -> tuple[int, int, int]:
        if not 1 <= limit <= 100_000:
            raise ValueError("incident rebuild limit must be between 1 and 100000")
        alert_ids = list(
            await self.session.scalars(
                select(Alert.id)
                .outerjoin(IncidentAlert, IncidentAlert.alert_id == Alert.id)
                .where(IncidentAlert.alert_id.is_(None))
                .order_by(Alert.first_event_at, Alert.id)
                .limit(limit)
            )
        )
        created = 0
        updated = 0
        for alert_id in alert_ids:
            outcome = await self.process_alert(alert_id)
            if outcome.created:
                created += 1
            else:
                updated += 1
        return len(alert_ids), created, updated

    @staticmethod
    def score_candidate(
        context: AlertContext,
        incident: Incident,
        connections: set[tuple[UUID, UUID]],
    ) -> CandidateScore:
        config = CORRELATION_CONFIG
        signals: list[CorrelationSignal] = []
        existing_links = [
            link for link in incident.alert_links if link.alert.status != AlertStatus.FALSE_POSITIVE
        ]
        incident_assets = {link.asset_id for link in incident.asset_links}
        incident_sources = {link.alert.source_ip for link in existing_links if link.alert.source_ip}
        incident_users = {link.alert.username for link in existing_links if link.alert.username}

        if incident.scenario_run_id and incident.scenario_run_id in context.scenario_run_ids:
            signals.append(
                CorrelationSignal(
                    type="shared_scenario_run",
                    weight=config.same_scenario_weight,
                    strength="strong",
                    description="Alerts share the same explicitly attributed ScenarioRun.",
                    details={"scenario_run_id": str(incident.scenario_run_id)},
                )
            )
        shared_sources = sorted(context.source_ips & incident_sources)
        if shared_sources:
            signals.append(
                CorrelationSignal(
                    type="shared_source_ip",
                    weight=config.shared_source_ip_weight,
                    strength="strong",
                    description=f"Alerts share source IP {shared_sources[0]}.",
                    details={"source_ips": shared_sources},
                )
            )
        shared_users = sorted(context.usernames & incident_users)
        if shared_users:
            signals.append(
                CorrelationSignal(
                    type="shared_username",
                    weight=config.shared_username_weight,
                    strength="strong",
                    description=f"Alerts share username {shared_users[0]}.",
                    details={"usernames": shared_users},
                )
            )
        shared_assets = sorted(context.asset_ids & incident_assets, key=str)
        if shared_assets:
            signals.append(
                CorrelationSignal(
                    type="shared_asset",
                    weight=config.shared_asset_weight,
                    strength="strong",
                    description="Alerts involve at least one shared asset.",
                    details={"asset_ids": [str(item) for item in shared_assets]},
                )
            )
        elif CorrelationService._has_network_relationship(
            context.asset_ids, incident_assets, connections
        ):
            signals.append(
                CorrelationSignal(
                    type="observed_network_relationship",
                    weight=config.network_relationship_weight,
                    strength="moderate",
                    description="Affected assets have an observed network relationship.",
                )
            )

        new_rule = context.alert.detection_rule.rule_id
        progression_pairs = [
            (link.alert.detection_rule.rule_id, new_rule)
            for link in existing_links
            if _as_utc(link.alert.last_event_at) <= _as_utc(context.alert.first_event_at)
            and (link.alert.detection_rule.rule_id, new_rule) in DETECTION_PROGRESSION
        ]
        if progression_pairs:
            previous, current = progression_pairs[-1]
            signals.append(
                CorrelationSignal(
                    type="detection_progression",
                    weight=config.progression_weight,
                    strength="moderate",
                    description=(
                        f"Observed rule order matches correlation hint {previous} to {current}."
                    ),
                    details={"previous_rule_id": previous, "current_rule_id": current},
                )
            )

        gap = CorrelationService._time_gap_seconds(context.alert, incident)
        if gap <= 120:
            time_weight = config.within_two_minutes_weight
            label = "within two minutes"
            strength = "moderate"
        elif gap <= 300:
            time_weight = config.within_five_minutes_weight
            label = "within five minutes"
            strength = "moderate"
        else:
            time_weight = config.within_window_weight
            label = "within the bounded correlation window"
            strength = "supporting"
        signals.append(
            CorrelationSignal(
                type="time_proximity",
                weight=time_weight,
                strength=strength,
                description=f"Alert activity occurred {label}.",
                details={"gap_seconds": gap},
            )
        )
        return CandidateScore(
            incident=incident,
            score=min(100, sum(signal.weight for signal in signals)),
            signals=tuple(signals),
        )

    async def _alert(self, alert_id: UUID) -> Alert | None:
        return await self.session.scalar(
            select(Alert)
            .where(Alert.id == alert_id)
            .options(
                joinedload(Alert.detection_rule),
                joinedload(Alert.asset),
                selectinload(Alert.evidence_events),
                selectinload(Alert.incident_link),
            )
        )

    @staticmethod
    def _context(alert: Alert) -> AlertContext:
        asset_ids = {alert.asset_id} if alert.asset_id else set()
        asset_ids.update(event.asset_id for event in alert.evidence_events if event.asset_id)
        source_ips = {alert.source_ip} if alert.source_ip else set()
        source_ips.update(event.source_ip for event in alert.evidence_events if event.source_ip)
        usernames = {alert.username} if alert.username else set()
        usernames.update(event.username for event in alert.evidence_events if event.username)
        scenario_ids = {
            event.scenario_run_id for event in alert.evidence_events if event.scenario_run_id
        }
        return AlertContext(
            alert=alert,
            events=alert.evidence_events,
            asset_ids=frozenset(asset_ids),
            source_ips=frozenset(source_ips),
            usernames=frozenset(usernames),
            scenario_run_ids=frozenset(scenario_ids),
        )

    @staticmethod
    def _scenario_conflict(context: AlertContext, incident: Incident) -> bool:
        return bool(
            incident.scenario_run_id
            and context.scenario_run_ids
            and incident.scenario_run_id not in context.scenario_run_ids
        )

    async def _database_lock(self, context: AlertContext) -> None:
        if not self.session.bind or self.session.bind.dialect.name != "postgresql":
            return
        identity = (
            f"scenario:{sorted(map(str, context.scenario_run_ids))[0]}"
            if context.scenario_run_ids
            else "|".join(
                [
                    sorted(context.source_ips)[0] if context.source_ips else "no-source",
                    sorted(context.usernames)[0] if context.usernames else "no-user",
                    sorted(map(str, context.asset_ids))[0] if context.asset_ids else "no-asset",
                ]
            )
        )
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:identity))"), {"identity": identity}
        )

    @staticmethod
    def _has_network_relationship(
        source_ids: frozenset[UUID],
        candidate_ids: set[UUID],
        connections: set[tuple[UUID, UUID]],
    ) -> bool:
        return any(
            (source, destination) in connections or (destination, source) in connections
            for source in source_ids
            for destination in candidate_ids
        )

    @staticmethod
    def _time_gap_seconds(alert: Alert, incident: Incident) -> int:
        alert_start = _as_utc(alert.first_event_at)
        alert_end = _as_utc(alert.last_event_at)
        incident_start = _as_utc(incident.first_activity_at)
        incident_end = _as_utc(incident.last_activity_at)
        if alert_start > incident_end:
            return round((alert_start - incident_end).total_seconds())
        if incident_start > alert_end:
            return round((incident_start - alert_end).total_seconds())
        return 0

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return _as_utc(value)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
