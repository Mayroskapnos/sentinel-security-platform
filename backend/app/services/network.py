import asyncio
import hashlib
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid5

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.errors import NotFoundError
from app.models.alert import Alert, AlertEvent
from app.models.asset import Asset
from app.models.enums import AlertStatus
from app.models.network_connection import NetworkConnection
from app.models.scenario_run import ScenarioRun
from app.models.security_event import SecurityEvent
from app.schemas.common import Page
from app.schemas.network import (
    NetworkConnectionFilters,
    NetworkConnectionResponse,
    NetworkConnectionUpdate,
    NetworkTopologyResponse,
    ObservedTechnique,
    TopologyActivity,
    TopologyAlertReference,
    TopologyEdge,
    TopologyNode,
    TopologyScenarioContext,
    TopologySummary,
    TopologyWindow,
)

CONNECTION_EVENT_TYPES = {
    "authentication",
    "database_connection",
    "database_session",
    "http_request",
    "network_connection",
}
ACTIVITY_EVENT_TYPES = CONNECTION_EVENT_TYPES | {"database_query", "privilege"}
ACTIVE_ALERT_STATUSES = (AlertStatus.NEW, AlertStatus.INVESTIGATING)
MAX_TOPOLOGY_EVENTS = 5_000
MAX_EDGE_EVENT_IDS = 25
BACKFILL_EVENT_LIMIT = 100_000
TOPOLOGY_EDGE_NAMESPACE = UUID("8a222a37-a5b3-4e55-b1b0-8cf708c2e08a")
aggregation_lock = asyncio.Lock()


@dataclass(frozen=True)
class ConnectionObservation:
    key: str
    source_asset: Asset
    destination_asset: Asset
    source_ip: str
    destination_ip: str
    source_port: int | None
    destination_port: int | None
    protocol: str
    connection_type: str


@dataclass
class EventAggregate:
    observation: ConnectionObservation
    first_seen: datetime
    last_seen: datetime
    count: int
    last_status: str
    last_event: SecurityEvent
    event_ids: list[UUID]
    scenario_run_ids: set[UUID]


class NetworkService:
    """Persist and query topology only from observed telemetry and known assets."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @staticmethod
    def _safe_label(value: Any, fallback: str) -> str:
        if not isinstance(value, str):
            return fallback
        normalized = value.strip().lower()[:64]
        return normalized or fallback

    @staticmethod
    def _assets_by_ip(assets: list[Asset]) -> dict[str, Asset]:
        result = {asset.ip_address: asset for asset in assets}
        for asset in assets:
            aliases = asset.metadata_json.get("ip_aliases", [])
            if not isinstance(aliases, list):
                continue
            for alias in aliases:
                if isinstance(alias, str) and alias not in result:
                    result[alias] = asset
        return result

    @classmethod
    def observation_for(
        cls, event: SecurityEvent, assets_by_ip: dict[str, Asset]
    ) -> ConnectionObservation | None:
        if event.event_type not in CONNECTION_EVENT_TYPES:
            return None
        if not event.source_ip or not event.destination_ip:
            return None
        source_asset = assets_by_ip.get(event.source_ip)
        destination_asset = assets_by_ip.get(event.destination_ip)
        if source_asset is None or destination_asset is None:
            return None
        if source_asset.id == destination_asset.id:
            return None

        protocol = cls._safe_label(event.normalized_data.get("protocol"), "tcp")
        fallback_types = {
            "authentication": "ssh" if event.destination_port == 22 else "authentication",
            "database_connection": "postgresql",
            "database_session": "postgresql",
            "http_request": "http",
        }
        connection_type = cls._safe_label(
            event.normalized_data.get("service"),
            fallback_types.get(event.event_type, event.event_type),
        )
        identity = "|".join(
            (
                str(source_asset.id),
                str(destination_asset.id),
                protocol,
                str(event.destination_port) if event.destination_port is not None else "none",
                connection_type,
            )
        )
        return ConnectionObservation(
            key=hashlib.sha256(identity.encode("utf-8")).hexdigest(),
            source_asset=source_asset,
            destination_asset=destination_asset,
            source_ip=event.source_ip,
            destination_ip=event.destination_ip,
            source_port=event.source_port,
            destination_port=event.destination_port,
            protocol=protocol,
            connection_type=connection_type,
        )

    @staticmethod
    def _metadata(event: SecurityEvent) -> dict[str, Any]:
        return {
            "last_event_id": str(event.id),
            "last_event_type": event.event_type,
            "last_event_source": event.source,
            "last_scenario_run_id": (str(event.scenario_run_id) if event.scenario_run_id else None),
        }

    async def aggregate_event(self, event_id: UUID) -> NetworkConnectionUpdate | None:
        event = await self.session.get(SecurityEvent, event_id)
        if event is None or event.event_type not in CONNECTION_EVENT_TYPES:
            return None
        assets = list(await self.session.scalars(select(Asset)))
        observation = self.observation_for(event, self._assets_by_ip(assets))
        if observation is None:
            return None

        async with aggregation_lock:
            connection = await self.session.scalar(
                select(NetworkConnection).where(
                    NetworkConnection.relationship_key == observation.key
                )
            )
            timestamp = self._as_utc(event.timestamp)
            if connection is None:
                connection = NetworkConnection(
                    relationship_key=observation.key,
                    source_asset_id=observation.source_asset.id,
                    destination_asset_id=observation.destination_asset.id,
                    source_ip=observation.source_ip,
                    destination_ip=observation.destination_ip,
                    source_port=observation.source_port,
                    destination_port=observation.destination_port,
                    protocol=observation.protocol,
                    connection_type=observation.connection_type,
                    first_seen=timestamp,
                    last_seen=timestamp,
                    connection_count=1,
                    last_status=event.status,
                    metadata_json=self._metadata(event),
                )
                self.session.add(connection)
            else:
                connection.connection_count += 1
                connection.first_seen = min(self._as_utc(connection.first_seen), timestamp)
                if timestamp >= self._as_utc(connection.last_seen):
                    connection.last_seen = timestamp
                    connection.last_status = event.status
                    connection.source_port = observation.source_port
                    connection.metadata_json = self._metadata(event)
            await self.session.commit()
            await self.session.refresh(connection)
        return NetworkConnectionUpdate.model_validate(connection)

    async def list_connections(
        self, filters: NetworkConnectionFilters
    ) -> Page[NetworkConnectionResponse]:
        query = select(NetworkConnection)
        if filters.source_asset_id:
            query = query.where(NetworkConnection.source_asset_id == filters.source_asset_id)
        if filters.destination_asset_id:
            query = query.where(
                NetworkConnection.destination_asset_id == filters.destination_asset_id
            )
        if filters.protocol:
            query = query.where(NetworkConnection.protocol == filters.protocol.lower())
        if filters.destination_port is not None:
            query = query.where(NetworkConnection.destination_port == filters.destination_port)
        if filters.start_time:
            query = query.where(NetworkConnection.last_seen >= filters.start_time)
        total = int(
            await self.session.scalar(
                select(func.count()).select_from(query.order_by(None).subquery())
            )
            or 0
        )
        rows = list(
            await self.session.scalars(
                query.options(
                    joinedload(NetworkConnection.source_asset),
                    joinedload(NetworkConnection.destination_asset),
                )
                .order_by(NetworkConnection.last_seen.desc(), NetworkConnection.id)
                .offset((filters.page - 1) * filters.page_size)
                .limit(filters.page_size)
            )
        )
        return Page[NetworkConnectionResponse].create(
            items=[NetworkConnectionResponse.model_validate(row) for row in rows],
            page=filters.page,
            page_size=filters.page_size,
            total=total,
        )

    @staticmethod
    def _window_start(window: TopologyWindow, now: datetime) -> datetime | None:
        durations = {
            "5m": timedelta(minutes=5),
            "15m": timedelta(minutes=15),
            "1h": timedelta(hours=1),
            "24h": timedelta(hours=24),
        }
        return now - durations[window] if window != "all" else None

    async def topology(
        self,
        window: TopologyWindow,
        scenario_run_id: UUID | None = None,
        asset_id: UUID | None = None,
        alert_id: UUID | None = None,
    ) -> NetworkTopologyResponse:
        now = datetime.now(UTC)
        start = self._window_start(window, now)
        scenario = None
        if scenario_run_id:
            run = await self.session.get(ScenarioRun, scenario_run_id)
            if run is None:
                raise NotFoundError(
                    "SCENARIO_RUN_NOT_FOUND", "Requested scenario run does not exist."
                )
            scenario_event_count = int(
                await self.session.scalar(
                    select(func.count(SecurityEvent.id)).where(
                        SecurityEvent.scenario_run_id == scenario_run_id
                    )
                )
                or 0
            )
            scenario_alert_count = int(
                await self.session.scalar(
                    select(func.count(func.distinct(AlertEvent.alert_id)))
                    .join(SecurityEvent, SecurityEvent.id == AlertEvent.event_id)
                    .where(SecurityEvent.scenario_run_id == scenario_run_id)
                )
                or 0
            )
            scenario = TopologyScenarioContext(
                run_id=run.id,
                scenario_id=run.scenario_id,
                scenario_name=run.scenario_name,
                status=run.status,
                event_count=scenario_event_count,
                alert_count=scenario_alert_count,
                started_at=run.started_at,
                finished_at=run.finished_at,
            )

        assets = list(await self.session.scalars(select(Asset).order_by(Asset.hostname)))
        assets_by_ip = self._assets_by_ip(assets)
        assets_by_id = {asset.id: asset for asset in assets}

        event_query = select(SecurityEvent).where(
            SecurityEvent.event_type.in_(ACTIVITY_EVENT_TYPES)
        )
        if scenario_run_id:
            event_query = event_query.where(SecurityEvent.scenario_run_id == scenario_run_id)
        elif start:
            event_query = event_query.where(SecurityEvent.timestamp >= start)
        newest = list(
            await self.session.scalars(
                event_query.order_by(SecurityEvent.timestamp.desc(), SecurityEvent.id.desc()).limit(
                    MAX_TOPOLOGY_EVENTS + 1
                )
            )
        )
        activity_truncated = len(newest) > MAX_TOPOLOGY_EVENTS
        events = list(reversed(newest[:MAX_TOPOLOGY_EVENTS]))
        aggregates: dict[str, EventAggregate] = {}
        node_event_counts: dict[UUID, int] = defaultdict(int)
        relevant_node_ids: set[UUID] = set()
        activities: list[TopologyActivity] = []
        for event in events:
            source_asset = assets_by_ip.get(event.source_ip or "")
            destination_asset = assets_by_ip.get(event.destination_ip or "")
            activity_asset_ids = {
                item.id
                for item in (source_asset, destination_asset, assets_by_id.get(event.asset_id))
                if item is not None
            }
            relevant_node_ids.update(activity_asset_ids)
            for node_id in activity_asset_ids:
                node_event_counts[node_id] += 1
            activities.append(
                TopologyActivity(
                    id=event.id,
                    timestamp=event.timestamp,
                    event_type=event.event_type,
                    action=event.action,
                    status=event.status,
                    source_asset_id=source_asset.id if source_asset else None,
                    destination_asset_id=(destination_asset.id if destination_asset else None),
                    source_ip=event.source_ip,
                    destination_ip=event.destination_ip,
                    destination_port=event.destination_port,
                    scenario_run_id=event.scenario_run_id,
                )
            )
            observation = self.observation_for(event, assets_by_ip)
            if observation is None:
                continue
            timestamp = self._as_utc(event.timestamp)
            aggregate = aggregates.get(observation.key)
            if aggregate is None:
                aggregates[observation.key] = EventAggregate(
                    observation=observation,
                    first_seen=timestamp,
                    last_seen=timestamp,
                    count=1,
                    last_status=event.status,
                    last_event=event,
                    event_ids=[event.id],
                    scenario_run_ids={event.scenario_run_id} if event.scenario_run_id else set(),
                )
            else:
                aggregate.count += 1
                aggregate.first_seen = min(aggregate.first_seen, timestamp)
                if timestamp >= aggregate.last_seen:
                    aggregate.last_seen = timestamp
                    aggregate.last_status = event.status
                    aggregate.last_event = event
                if len(aggregate.event_ids) < MAX_EDGE_EVENT_IDS:
                    aggregate.event_ids.append(event.id)
                if event.scenario_run_id:
                    aggregate.scenario_run_ids.add(event.scenario_run_id)

        connection_query = select(NetworkConnection).options(
            joinedload(NetworkConnection.source_asset),
            joinedload(NetworkConnection.destination_asset),
        )
        if scenario_run_id:
            connection_query = connection_query.where(
                NetworkConnection.relationship_key.in_(aggregates.keys())
            )
        elif start:
            connection_query = connection_query.where(NetworkConnection.last_seen >= start)
        connections = list(await self.session.scalars(connection_query))
        connections_by_key = {item.relationship_key: item for item in connections}

        active_alert_query = select(Alert).where(Alert.status.in_(ACTIVE_ALERT_STATUSES))
        active_alerts = list(
            await self.session.scalars(active_alert_query.options(joinedload(Alert.detection_rule)))
        )
        if scenario_run_id:
            display_alerts = list(
                (
                    await self.session.scalars(
                        select(Alert)
                        .join(AlertEvent, AlertEvent.alert_id == Alert.id)
                        .join(SecurityEvent, SecurityEvent.id == AlertEvent.event_id)
                        .where(SecurityEvent.scenario_run_id == scenario_run_id)
                        .options(joinedload(Alert.detection_rule))
                        .order_by(Alert.timestamp, Alert.id)
                    )
                ).unique()
            )
        else:
            display_alerts = active_alerts
        if alert_id and all(item.id != alert_id for item in display_alerts):
            requested_alert = await self.session.scalar(
                select(Alert).where(Alert.id == alert_id).options(joinedload(Alert.detection_rule))
            )
            if requested_alert:
                display_alerts.append(requested_alert)

        node_alert_ids: dict[UUID, set[UUID]] = defaultdict(set)
        for alert in active_alerts:
            candidate_ids = {alert.asset_id} if alert.asset_id else set()
            for ip in (alert.source_ip, alert.destination_ip):
                matched = assets_by_ip.get(ip or "")
                if matched:
                    candidate_ids.add(matched.id)
            for node_id in candidate_ids:
                node_alert_ids[node_id].add(alert.id)

        display_alert_ids = {alert.id for alert in display_alerts}
        evidence_rows = []
        if display_alert_ids:
            evidence_rows = list(
                await self.session.execute(
                    select(AlertEvent.alert_id, SecurityEvent)
                    .join(SecurityEvent, SecurityEvent.id == AlertEvent.event_id)
                    .where(AlertEvent.alert_id.in_(display_alert_ids))
                )
            )
        edge_alert_ids: dict[str, set[UUID]] = defaultdict(set)
        for evidence_alert_id, evidence_event in evidence_rows:
            observation = self.observation_for(evidence_event, assets_by_ip)
            if observation:
                edge_alert_ids[observation.key].add(evidence_alert_id)

        edges: list[TopologyEdge] = []
        edge_source = (
            aggregates.keys()
            if scenario_run_id
            else (connection.relationship_key for connection in connections)
        )
        for key in sorted(edge_source):
            aggregate = aggregates.get(key)
            connection = connections_by_key.get(key)
            if scenario_run_id and aggregate is None:
                continue
            if connection:
                source_asset_id = connection.source_asset_id
                destination_asset_id = connection.destination_asset_id
                source_ip = connection.source_ip
                destination_ip = connection.destination_ip
                source_port = (
                    aggregate.observation.source_port if aggregate else connection.source_port
                )
                destination_port = connection.destination_port
                protocol = connection.protocol
                connection_type = connection.connection_type
                first_seen = aggregate.first_seen if scenario_run_id else connection.first_seen
                last_seen = aggregate.last_seen if scenario_run_id else connection.last_seen
                connection_count = (
                    aggregate.count if scenario_run_id else connection.connection_count
                )
                last_status = aggregate.last_status if scenario_run_id else connection.last_status
                edge_id = connection.id
            else:
                assert aggregate is not None
                observation = aggregate.observation
                source_asset_id = observation.source_asset.id
                destination_asset_id = observation.destination_asset.id
                source_ip = observation.source_ip
                destination_ip = observation.destination_ip
                source_port = observation.source_port
                destination_port = observation.destination_port
                protocol = observation.protocol
                connection_type = observation.connection_type
                first_seen = aggregate.first_seen
                last_seen = aggregate.last_seen
                connection_count = aggregate.count
                last_status = aggregate.last_status
                edge_id = uuid5(TOPOLOGY_EDGE_NAMESPACE, key)
            recency = now - self._as_utc(last_seen)
            activity_state = (
                "active"
                if recency <= timedelta(seconds=60)
                else "recent"
                if recency <= timedelta(minutes=15)
                else "historical"
            )
            edges.append(
                TopologyEdge(
                    id=edge_id,
                    source_asset_id=source_asset_id,
                    destination_asset_id=destination_asset_id,
                    source_ip=source_ip,
                    destination_ip=destination_ip,
                    source_port=source_port,
                    destination_port=destination_port,
                    protocol=protocol,
                    connection_type=connection_type,
                    first_seen=first_seen,
                    last_seen=last_seen,
                    connection_count=connection_count,
                    recent_event_count=(aggregate.count if aggregate else connection_count),
                    last_status=last_status,
                    activity_state=activity_state,
                    alert_ids=sorted(edge_alert_ids[key], key=str),
                    scenario_run_ids=(
                        sorted(aggregate.scenario_run_ids, key=str) if aggregate else []
                    ),
                    event_ids=aggregate.event_ids if aggregate else [],
                )
            )

        if scenario_run_id:
            visible_assets = [asset for asset in assets if asset.id in relevant_node_ids]
        else:
            visible_assets = assets
        incident_counts: dict[UUID, int] = defaultdict(int)
        for edge in edges:
            incident_counts[edge.source_asset_id] += 1
            incident_counts[edge.destination_asset_id] += 1
        nodes = [
            TopologyNode(
                id=asset.id,
                hostname=asset.hostname,
                display_name=asset.display_name,
                ip_address=asset.ip_address,
                asset_type=asset.asset_type,
                operating_system=asset.operating_system,
                environment=asset.environment,
                network_zone=asset.network_zone,
                status=asset.status,
                risk_score=asset.risk_score,
                criticality=asset.criticality,
                first_seen=asset.first_seen,
                last_seen=asset.last_seen,
                open_alert_count=len(node_alert_ids[asset.id]),
                recent_event_count=node_event_counts[asset.id],
                recent_connection_count=incident_counts[asset.id],
                alert_ids=sorted(node_alert_ids[asset.id], key=str),
            )
            for asset in visible_assets
        ]

        alert_references = [
            TopologyAlertReference(
                id=alert.id,
                title=alert.title,
                severity=alert.severity,
                status=alert.status,
                rule_id=alert.detection_rule.rule_id,
                timestamp=alert.timestamp,
            )
            for alert in sorted(
                display_alerts, key=lambda item: (self._as_utc(item.timestamp), str(item.id))
            )
        ]
        techniques: dict[tuple[str, str, str], set[UUID]] = defaultdict(set)
        for alert in display_alerts:
            if alert.mitre_technique_id and alert.mitre_technique_name and alert.mitre_tactic:
                techniques[
                    (
                        alert.mitre_technique_id,
                        alert.mitre_technique_name,
                        alert.mitre_tactic,
                    )
                ].add(alert.id)
        observed_techniques = [
            ObservedTechnique(
                technique_id=technique_id,
                technique_name=technique_name,
                tactic=tactic,
                alert_ids=sorted(ids, key=str),
            )
            for (technique_id, technique_name, tactic), ids in sorted(techniques.items())
        ]

        if asset_id and asset_id not in assets_by_id:
            raise NotFoundError("ASSET_NOT_FOUND", "Requested asset does not exist.")
        return NetworkTopologyResponse(
            generated_at=now,
            window=window,
            scenario=scenario,
            nodes=nodes,
            edges=edges,
            alerts=alert_references,
            activities=activities,
            observed_techniques=observed_techniques,
            summary=TopologySummary(
                asset_count=len(nodes),
                connection_count=len(edges),
                active_connection_count=sum(edge.activity_state == "active" for edge in edges),
                open_alert_count=len(active_alerts),
                high_risk_asset_count=sum(node.risk_score >= 60 for node in nodes),
                activity_count=len(activities),
                activity_truncated=activity_truncated,
            ),
        )

    async def rebuild(self, limit: int = BACKFILL_EVENT_LIMIT) -> tuple[int, int]:
        event_count = int(
            await self.session.scalar(
                select(func.count(SecurityEvent.id)).where(
                    SecurityEvent.event_type.in_(CONNECTION_EVENT_TYPES)
                )
            )
            or 0
        )
        if event_count > limit:
            raise RuntimeError(
                f"network rebuild requires {event_count} events; safety limit is {limit}"
            )
        assets = list(await self.session.scalars(select(Asset)))
        assets_by_ip = self._assets_by_ip(assets)
        events = list(
            await self.session.scalars(
                select(SecurityEvent)
                .where(SecurityEvent.event_type.in_(CONNECTION_EVENT_TYPES))
                .order_by(SecurityEvent.timestamp, SecurityEvent.id)
            )
        )
        desired: dict[str, EventAggregate] = {}
        for event in events:
            observation = self.observation_for(event, assets_by_ip)
            if observation is None:
                continue
            timestamp = self._as_utc(event.timestamp)
            aggregate = desired.get(observation.key)
            if aggregate is None:
                desired[observation.key] = EventAggregate(
                    observation=observation,
                    first_seen=timestamp,
                    last_seen=timestamp,
                    count=1,
                    last_status=event.status,
                    last_event=event,
                    event_ids=[],
                    scenario_run_ids=set(),
                )
            else:
                aggregate.count += 1
                aggregate.first_seen = min(aggregate.first_seen, timestamp)
                if timestamp >= aggregate.last_seen:
                    aggregate.last_seen = timestamp
                    aggregate.last_status = event.status
                    aggregate.last_event = event
        existing = {
            item.relationship_key: item
            for item in await self.session.scalars(select(NetworkConnection))
        }
        stale_keys = set(existing) - set(desired)
        if stale_keys:
            await self.session.execute(
                delete(NetworkConnection).where(NetworkConnection.relationship_key.in_(stale_keys))
            )
        for key, aggregate in desired.items():
            observation = aggregate.observation
            connection = existing.get(key)
            if connection is None:
                connection = NetworkConnection(relationship_key=key)
                self.session.add(connection)
            connection.source_asset_id = observation.source_asset.id
            connection.destination_asset_id = observation.destination_asset.id
            connection.source_ip = observation.source_ip
            connection.destination_ip = observation.destination_ip
            connection.source_port = observation.source_port
            connection.destination_port = observation.destination_port
            connection.protocol = observation.protocol
            connection.connection_type = observation.connection_type
            connection.first_seen = aggregate.first_seen
            connection.last_seen = aggregate.last_seen
            connection.connection_count = aggregate.count
            connection.last_status = aggregate.last_status
            connection.metadata_json = self._metadata(aggregate.last_event)
        await self.session.commit()
        return len(events), len(desired)
