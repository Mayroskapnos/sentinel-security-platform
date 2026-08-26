from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.realtime.manager import websocket_manager
from app.schemas.common import Page
from app.schemas.incident import IncidentDetail, IncidentFilters, IncidentListItem, IncidentUpdate
from app.schemas.realtime import IncidentUpdatedMessage
from app.services.incidents import IncidentService

router = APIRouter(prefix="/incidents", tags=["incidents"])
SessionDependency = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("", response_model=Page[IncidentListItem], summary="List correlated incidents")
async def list_incidents(
    session: SessionDependency,
    filters: Annotated[IncidentFilters, Query()],
) -> Page[IncidentListItem]:
    return await IncidentService(session).list(filters)


@router.get("/{incident_id}", response_model=IncidentDetail, summary="Get incident detail")
async def get_incident(incident_id: UUID, session: SessionDependency) -> IncidentDetail:
    return await IncidentService(session).get(incident_id)


@router.patch(
    "/{incident_id}", response_model=IncidentDetail, summary="Update incident workflow state"
)
async def update_incident(
    incident_id: UUID, payload: IncidentUpdate, session: SessionDependency
) -> IncidentDetail:
    response = await IncidentService(session).update(incident_id, payload)
    await websocket_manager.broadcast(
        IncidentUpdatedMessage(data=IncidentListItem.model_validate(response.model_dump()))
    )
    return response
