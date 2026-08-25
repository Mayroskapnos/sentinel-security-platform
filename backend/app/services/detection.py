import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.alert import Alert, AlertEvent
from app.models.asset import Asset
from app.models.detection_rule import DetectionRule
from app.models.enums import AlertStatus, RuleType
from app.models.security_event import SecurityEvent
from app.repositories.alerts import AlertRepository
from app.repositories.detection_rules import DetectionRuleRepository
from app.schemas.alert import AlertResponse
from app.schemas.detection_rule import BundledRuleDefinition, RuleMatch
from app.services.risk import RiskService

logger = logging.getLogger(__name__)
evaluation_lock = asyncio.Lock()
ACTIVE_ALERT_STATUSES = [AlertStatus.NEW, AlertStatus.INVESTIGATING]
MAX_EVIDENCE_EVENTS = 500


@dataclass(frozen=True)
class DetectionResult:
    alert: AlertResponse
    created: bool


@dataclass(frozen=True)
class RuleMatchResult:
    events: list[SecurityEvent]
    observed_count: int
    timeframe_seconds: int | None
    explanation: str


class DetectionEngine:
    """Evaluate one already-persisted event against enabled, event-type candidates."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.rule_repository = DetectionRuleRepository(session)
        self.alert_repository = AlertRepository(session)
        self.risk_service = RiskService(session)

    async def evaluate(self, event_id: UUID) -> list[DetectionResult]:
        async with evaluation_lock:
            event = await self.session.scalar(
                select(SecurityEvent)
                .where(SecurityEvent.id == event_id)
                .options(joinedload(SecurityEvent.asset))
            )
            if event is None:
                logger.error("detection_event_missing event_id=%s", event_id)
                return []
            candidates = await self.rule_repository.candidates(event.event_type)
            results: list[DetectionResult] = []
            for rule in candidates:
                try:
                    result = await self._evaluate_rule(rule, event)
                    if result is not None:
                        results.append(result)
                except Exception as exc:
                    await self.session.rollback()
                    logger.exception(
                        "detection_rule_evaluation_failed rule_id=%s event_id=%s error_category=%s",
                        rule.rule_id,
                        event.id,
                        type(exc).__name__,
                    )
            return results

    async def _evaluate_rule(
        self, rule: DetectionRule, event: SecurityEvent
    ) -> DetectionResult | None:
        definition = self._definition(rule)
        if not self._matches(event, definition.match):
            return None
        context_assets = await self._context_assets(event)
        if not self._context_matches(definition, context_assets):
            return None

        if definition.rule_type == RuleType.THRESHOLD:
            match_result = await self._threshold_match(definition, event)
        elif definition.rule_type == RuleType.SEQUENCE:
            match_result = await self._sequence_match(definition, event)
        else:
            match_result = RuleMatchResult(
                events=[event],
                observed_count=1,
                timeframe_seconds=None,
                explanation="The incoming event matched every configured field and asset context.",
            )
        if match_result is None:
            return None
        return await self._create_or_suppress(rule, definition, event, match_result, context_assets)

    @staticmethod
    def _definition(rule: DetectionRule) -> BundledRuleDefinition:
        return BundledRuleDefinition.model_validate(
            {
                "id": rule.rule_id,
                "name": rule.name,
                "description": rule.description,
                "type": rule.rule_type,
                "severity": rule.severity,
                "enabled": rule.enabled,
                **rule.configuration,
                "mitre": (
                    {
                        "tactic": rule.mitre_tactic,
                        "technique_id": rule.mitre_technique_id,
                        "technique_name": rule.mitre_technique_name,
                    }
                    if rule.mitre_tactic and rule.mitre_technique_id and rule.mitre_technique_name
                    else None
                ),
            }
        )

    @staticmethod
    def _matches(event: SecurityEvent, match: RuleMatch) -> bool:
        for field, expected in match.model_dump(exclude_none=True, mode="json").items():
            actual = getattr(event, field)
            if actual != expected:
                return False
        return True

    async def _context_assets(self, event: SecurityEvent) -> tuple[Asset | None, Asset | None]:
        source_asset = (
            await self.session.scalar(select(Asset).where(Asset.ip_address == event.source_ip))
            if event.source_ip
            else None
        )
        destination_asset = (
            await self.session.scalar(select(Asset).where(Asset.ip_address == event.destination_ip))
            if event.destination_ip
            else None
        )
        return source_asset, destination_asset

    @staticmethod
    def _context_matches(
        definition: BundledRuleDefinition,
        assets: tuple[Asset | None, Asset | None],
    ) -> bool:
        if definition.context is None:
            return True
        source_asset, destination_asset = assets
        checks = (
            (definition.context.source_asset_type, source_asset, "asset_type"),
            (definition.context.source_network_zone, source_asset, "network_zone"),
            (definition.context.destination_asset_type, destination_asset, "asset_type"),
            (definition.context.destination_network_zone, destination_asset, "network_zone"),
        )
        return all(
            expected is None or (asset is not None and getattr(asset, attribute) == expected)
            for expected, asset, attribute in checks
        )

    async def _threshold_match(
        self, definition: BundledRuleDefinition, event: SecurityEvent
    ) -> RuleMatchResult | None:
        assert definition.threshold is not None
        start = self._as_utc(event.timestamp) - timedelta(
            seconds=definition.threshold.timeframe_seconds
        )
        query = self._window_query(definition.match, definition.group_by, event, start)
        if definition.threshold.distinct_field:
            count_expression = func.count(
                func.distinct(getattr(SecurityEvent, definition.threshold.distinct_field))
            )
        else:
            count_expression = func.count(SecurityEvent.id)
        observed_count = int(
            await self.session.scalar(query.with_only_columns(count_expression)) or 0
        )
        if observed_count < definition.threshold.count:
            return None
        events = list(
            await self.session.scalars(
                query.order_by(SecurityEvent.timestamp, SecurityEvent.id).limit(MAX_EVIDENCE_EVENTS)
            )
        )
        counted = (
            f"{observed_count} distinct {definition.threshold.distinct_field} values"
            if definition.threshold.distinct_field
            else f"{observed_count} matching events"
        )
        return RuleMatchResult(
            events=events,
            observed_count=observed_count,
            timeframe_seconds=definition.threshold.timeframe_seconds,
            explanation=(
                f"Observed {counted} in {definition.threshold.timeframe_seconds} seconds; "
                f"the rule requires {definition.threshold.count}."
            ),
        )

    async def _sequence_match(
        self, definition: BundledRuleDefinition, event: SecurityEvent
    ) -> RuleMatchResult | None:
        assert definition.sequence is not None
        start = self._as_utc(event.timestamp) - timedelta(
            seconds=definition.sequence.timeframe_seconds
        )
        query = self._window_query(
            definition.sequence.preceding, definition.group_by, event, start
        ).where(SecurityEvent.id != event.id)
        observed_count = int(
            await self.session.scalar(query.with_only_columns(func.count(SecurityEvent.id))) or 0
        )
        if observed_count < definition.sequence.count:
            return None
        preceding = list(
            await self.session.scalars(
                query.order_by(SecurityEvent.timestamp, SecurityEvent.id).limit(
                    MAX_EVIDENCE_EVENTS - 1
                )
            )
        )
        return RuleMatchResult(
            events=[*preceding, event],
            observed_count=observed_count,
            timeframe_seconds=definition.sequence.timeframe_seconds,
            explanation=(
                f"Observed {observed_count} prerequisite events followed by the matching event "
                f"within {definition.sequence.timeframe_seconds} seconds; the rule requires "
                f"{definition.sequence.count}."
            ),
        )

    @staticmethod
    def _window_query(
        match: RuleMatch,
        group_by: list[str],
        incoming: SecurityEvent,
        start: datetime,
    ):
        query = select(SecurityEvent).where(
            SecurityEvent.timestamp >= start,
            SecurityEvent.timestamp <= incoming.timestamp,
        )
        for field, expected in match.model_dump(exclude_none=True, mode="json").items():
            query = query.where(getattr(SecurityEvent, field) == expected)
        for field in group_by:
            query = query.where(getattr(SecurityEvent, field) == getattr(incoming, field))
        return query

    async def _create_or_suppress(
        self,
        rule: DetectionRule,
        definition: BundledRuleDefinition,
        event: SecurityEvent,
        match: RuleMatchResult,
        context_assets: tuple[Asset | None, Asset | None],
    ) -> DetectionResult:
        deduplication_key = self._deduplication_key(definition, event)
        suppression_start = self._as_utc(event.timestamp) - timedelta(
            seconds=definition.suppression_seconds
        )
        existing = await self.session.scalar(
            select(Alert)
            .where(
                Alert.detection_rule_id == rule.id,
                Alert.deduplication_key == deduplication_key,
                Alert.status.in_(ACTIVE_ALERT_STATUSES),
                Alert.timestamp >= suppression_start,
                Alert.timestamp <= event.timestamp,
            )
            .order_by(Alert.timestamp.desc())
            .limit(1)
        )
        asset = self._alert_asset(event, context_assets)
        evidence = self._evidence(definition, match)
        if existing is None:
            alert = Alert(
                timestamp=event.timestamp,
                title=rule.name,
                description=rule.description,
                severity=rule.severity,
                status=AlertStatus.NEW,
                detection_rule_id=rule.id,
                asset_id=asset.id if asset else None,
                source_ip=event.source_ip,
                destination_ip=event.destination_ip,
                username=event.username,
                mitre_tactic=rule.mitre_tactic,
                mitre_technique_id=rule.mitre_technique_id,
                mitre_technique_name=rule.mitre_technique_name,
                evidence=evidence,
                metadata_json={
                    "rule_type": rule.rule_type,
                    "suppression_seconds": definition.suppression_seconds,
                },
                deduplication_key=deduplication_key,
                first_event_at=min(item.timestamp for item in match.events),
                last_event_at=max(item.timestamp for item in match.events),
                risk_score=self.risk_service.alert_score(
                    rule.severity, asset.criticality if asset else None, len(match.events)
                ),
            )
            self.session.add(alert)
            await self.session.flush()
            for evidence_event in match.events:
                self.session.add(AlertEvent(alert_id=alert.id, event_id=evidence_event.id))
            created = True
        else:
            alert = existing
            attached_ids = set(
                await self.session.scalars(
                    select(AlertEvent.event_id).where(AlertEvent.alert_id == alert.id)
                )
            )
            for evidence_event in match.events:
                if evidence_event.id not in attached_ids:
                    self.session.add(AlertEvent(alert_id=alert.id, event_id=evidence_event.id))
            combined_count = len(attached_ids | {item.id for item in match.events})
            evidence["event_count"] = combined_count
            evidence["suppressed_matches"] = int(alert.evidence.get("suppressed_matches", 0)) + 1
            alert.evidence = evidence
            first_timestamp = min(self._as_utc(item.timestamp) for item in match.events)
            last_timestamp = max(self._as_utc(item.timestamp) for item in match.events)
            alert.first_event_at = min(self._as_utc(alert.first_event_at), first_timestamp)
            alert.last_event_at = max(self._as_utc(alert.last_event_at), last_timestamp)
            alert.risk_score = self.risk_service.alert_score(
                rule.severity, asset.criticality if asset else None, combined_count
            )
            created = False

        await self.risk_service.recalculate_asset(alert.asset_id)
        await self.session.commit()
        refreshed = await self.alert_repository.get(alert.id)
        assert refreshed is not None
        logger.info(
            "detection_alert_%s alert_id=%s rule_id=%s event_id=%s evidence_count=%d",
            "created" if created else "updated",
            alert.id,
            rule.rule_id,
            event.id,
            refreshed.evidence_count,
        )
        return DetectionResult(alert=AlertResponse.model_validate(refreshed), created=created)

    @staticmethod
    def _alert_asset(
        event: SecurityEvent, assets: tuple[Asset | None, Asset | None]
    ) -> Asset | None:
        source_asset, destination_asset = assets
        if event.asset is not None:
            return event.asset
        return destination_asset or source_asset

    @staticmethod
    def _deduplication_key(definition: BundledRuleDefinition, event: SecurityEvent) -> str:
        groups = [f"{field}={getattr(event, field) or '<none>'}" for field in definition.group_by]
        return "|".join([definition.rule_id, *groups])

    @staticmethod
    def _evidence(definition: BundledRuleDefinition, match: RuleMatchResult) -> dict[str, Any]:
        return {
            "explanation": match.explanation,
            "observed_count": match.observed_count,
            "event_count": len(match.events),
            "timeframe_seconds": match.timeframe_seconds,
            "group_by": definition.group_by,
            "match": definition.match.model_dump(mode="json", exclude_none=True),
            "threshold": (
                definition.threshold.model_dump(mode="json") if definition.threshold else None
            ),
            "sequence": (
                definition.sequence.model_dump(mode="json") if definition.sequence else None
            ),
            "suppressed_matches": 0,
        }

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
