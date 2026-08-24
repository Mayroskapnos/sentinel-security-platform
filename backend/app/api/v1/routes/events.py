from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.common import Page
from app.schemas.security_event import (
    SecurityEventCreate,
    SecurityEventFilters,
    SecurityEventResponse,
)
from app.services.events import SecurityEventService

router = APIRouter(prefix="/events", tags=["events"])
SessionDependency = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("", response_model=Page[SecurityEventResponse], summary="List security events")
async def list_events(
    session: SessionDependency,
    filters: Annotated[SecurityEventFilters, Query()],
) -> Page[SecurityEventResponse]:
    return await SecurityEventService(session).list(filters)


@router.get("/{event_id}", response_model=SecurityEventResponse, summary="Get a security event")
async def get_event(event_id: UUID, session: SessionDependency) -> SecurityEventResponse:
    return await SecurityEventService(session).get(event_id)


@router.post(
    "",
    response_model=SecurityEventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a normalized security event",
)
async def create_event(
    payload: SecurityEventCreate, session: SessionDependency
) -> SecurityEventResponse:
    return await SecurityEventService(session).create(payload)
