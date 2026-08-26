from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.common import Page
from app.schemas.network import (
    NetworkConnectionFilters,
    NetworkConnectionResponse,
    NetworkTopologyResponse,
    TopologyWindow,
)
from app.services.network import NetworkService

router = APIRouter(prefix="/network", tags=["network"])
SessionDependency = Annotated[AsyncSession, Depends(get_db_session)]


@router.get(
    "/connections",
    response_model=Page[NetworkConnectionResponse],
    summary="List aggregated observed network relationships",
)
async def list_connections(
    session: SessionDependency,
    filters: Annotated[NetworkConnectionFilters, Query()],
) -> Page[NetworkConnectionResponse]:
    return await NetworkService(session).list_connections(filters)


@router.get(
    "/topology",
    response_model=NetworkTopologyResponse,
    summary="Get a bulk live or scenario-scoped topology",
)
async def get_topology(
    session: SessionDependency,
    window: TopologyWindow = "15m",
    scenario_run_id: UUID | None = None,
    incident_id: UUID | None = None,
    asset_id: UUID | None = None,
    alert_id: UUID | None = None,
) -> NetworkTopologyResponse:
    return await NetworkService(session).topology(
        window=window,
        scenario_run_id=scenario_run_id,
        incident_id=incident_id,
        asset_id=asset_id,
        alert_id=alert_id,
    )
