from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.dashboard import DashboardActivity, DashboardSummary
from app.services.dashboard import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
SessionDependency = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("/summary", response_model=DashboardSummary, summary="Get dashboard metrics")
async def get_dashboard_summary(session: SessionDependency) -> DashboardSummary:
    return await DashboardService(session).summary()


@router.get(
    "/activity", response_model=DashboardActivity, summary="Get aggregated security activity"
)
async def get_dashboard_activity(
    session: SessionDependency,
    hours: Annotated[int, Query(ge=1, le=168)] = 72,
) -> DashboardActivity:
    return await DashboardService(session).activity(hours)
