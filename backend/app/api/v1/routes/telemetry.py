from typing import Annotated

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.session import get_db_session
from app.schemas.security_event import SecurityEventCreate, SecurityEventResponse
from app.services.telemetry import TelemetryIngestionService

router = APIRouter(prefix="/telemetry", tags=["telemetry"])
SessionDependency = Annotated[AsyncSession, Depends(get_db_session)]


def validate_content_length(
    content_length: Annotated[int | None, Header(ge=0)] = None,
) -> None:
    maximum = get_settings().telemetry_max_body_bytes
    if content_length is not None and content_length > maximum:
        raise AppError(
            code="TELEMETRY_PAYLOAD_TOO_LARGE",
            message=f"Telemetry payload must not exceed {maximum} bytes.",
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
        )


@router.post(
    "/events",
    response_model=SecurityEventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest and broadcast normalized machine telemetry",
    dependencies=[Depends(validate_content_length)],
)
async def ingest_telemetry_event(
    payload: SecurityEventCreate,
    session: SessionDependency,
) -> SecurityEventResponse:
    return await TelemetryIngestionService(session).ingest(payload)
