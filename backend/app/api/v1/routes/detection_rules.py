from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.common import Page
from app.schemas.detection_rule import (
    DetectionRuleFilters,
    DetectionRuleResponse,
    DetectionRuleUpdate,
)
from app.services.detection_rules import DetectionRuleService

router = APIRouter(prefix="/rules", tags=["detection-rules"])
SessionDependency = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("", response_model=Page[DetectionRuleResponse], summary="List detection rules")
async def list_detection_rules(
    session: SessionDependency,
    filters: Annotated[DetectionRuleFilters, Query()],
) -> Page[DetectionRuleResponse]:
    return await DetectionRuleService(session).list(filters)


@router.get("/{rule_id}", response_model=DetectionRuleResponse, summary="Get a detection rule")
async def get_detection_rule(rule_id: UUID, session: SessionDependency) -> DetectionRuleResponse:
    return await DetectionRuleService(session).get(rule_id)


@router.patch(
    "/{rule_id}", response_model=DetectionRuleResponse, summary="Enable or disable a rule"
)
async def update_detection_rule(
    rule_id: UUID,
    payload: DetectionRuleUpdate,
    session: SessionDependency,
) -> DetectionRuleResponse:
    return await DetectionRuleService(session).update(rule_id, payload)
