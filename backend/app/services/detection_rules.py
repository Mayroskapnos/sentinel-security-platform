from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.repositories.detection_rules import DetectionRuleRepository
from app.schemas.common import Page
from app.schemas.detection_rule import (
    DetectionRuleFilters,
    DetectionRuleResponse,
    DetectionRuleUpdate,
)


class DetectionRuleService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = DetectionRuleRepository(session)

    async def list(self, filters: DetectionRuleFilters) -> Page[DetectionRuleResponse]:
        rules, total = await self.repository.list(filters)
        return Page[DetectionRuleResponse].create(
            items=[DetectionRuleResponse.model_validate(rule) for rule in rules],
            page=filters.page,
            page_size=filters.page_size,
            total=total,
        )

    async def get(self, rule_id: UUID) -> DetectionRuleResponse:
        rule = await self.repository.get(rule_id)
        if rule is None:
            raise NotFoundError(
                "DETECTION_RULE_NOT_FOUND", "Requested detection rule does not exist."
            )
        return DetectionRuleResponse.model_validate(rule)

    async def update(self, rule_id: UUID, payload: DetectionRuleUpdate) -> DetectionRuleResponse:
        rule = await self.repository.get(rule_id)
        if rule is None:
            raise NotFoundError(
                "DETECTION_RULE_NOT_FOUND", "Requested detection rule does not exist."
            )
        rule.enabled = payload.enabled
        await self.session.commit()
        await self.session.refresh(rule)
        return DetectionRuleResponse.model_validate(rule)
