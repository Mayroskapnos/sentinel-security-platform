from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.detection_rule import DetectionRule
from app.schemas.detection_rule import DetectionRuleFilters


class DetectionRuleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _filtered_query(filters: DetectionRuleFilters) -> Select[tuple[DetectionRule]]:
        query = select(DetectionRule)
        if filters.enabled is not None:
            query = query.where(DetectionRule.enabled == filters.enabled)
        if filters.rule_type:
            query = query.where(DetectionRule.rule_type == filters.rule_type)
        if filters.severity:
            query = query.where(DetectionRule.severity == filters.severity)
        if filters.event_type:
            query = query.where(DetectionRule.event_type == filters.event_type)
        if filters.search:
            pattern = f"%{filters.search.strip()}%"
            query = query.where(
                or_(
                    DetectionRule.rule_id.ilike(pattern),
                    DetectionRule.name.ilike(pattern),
                    DetectionRule.description.ilike(pattern),
                )
            )
        return query

    async def list(self, filters: DetectionRuleFilters) -> tuple[list[DetectionRule], int]:
        query = self._filtered_query(filters)
        total = await self.session.scalar(
            select(func.count()).select_from(query.order_by(None).subquery())
        )
        rules = await self.session.scalars(
            query.order_by(DetectionRule.rule_id)
            .offset((filters.page - 1) * filters.page_size)
            .limit(filters.page_size)
        )
        return list(rules), int(total or 0)

    async def get(self, rule_id: UUID) -> DetectionRule | None:
        return await self.session.get(DetectionRule, rule_id)

    async def candidates(self, event_type: str) -> list[DetectionRule]:
        rules = await self.session.scalars(
            select(DetectionRule)
            .where(
                DetectionRule.enabled.is_(True),
                or_(DetectionRule.event_type == event_type, DetectionRule.event_type.is_(None)),
            )
            .order_by(DetectionRule.rule_id)
        )
        return list(rules)
