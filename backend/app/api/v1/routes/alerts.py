from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.alert import AlertDetailResponse, AlertFilters, AlertResponse, AlertUpdate
from app.schemas.common import Page
from app.services.alerts import AlertService

router = APIRouter(prefix="/alerts", tags=["alerts"])
SessionDependency = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("", response_model=Page[AlertResponse], summary="List detection alerts")
async def list_alerts(
    session: SessionDependency,
    filters: Annotated[AlertFilters, Query()],
) -> Page[AlertResponse]:
    return await AlertService(session).list(filters)


@router.get("/{alert_id}", response_model=AlertDetailResponse, summary="Get a detection alert")
async def get_alert(alert_id: UUID, session: SessionDependency) -> AlertDetailResponse:
    return await AlertService(session).get(alert_id)


@router.patch("/{alert_id}", response_model=AlertResponse, summary="Update alert workflow status")
async def update_alert(
    alert_id: UUID, payload: AlertUpdate, session: SessionDependency
) -> AlertResponse:
    return await AlertService(session).update(alert_id, payload)
