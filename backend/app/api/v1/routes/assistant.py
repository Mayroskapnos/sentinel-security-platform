from fastapi import APIRouter

from app.db.session import async_session_factory
from app.schemas.investigation import AssistantStatus
from app.services.investigations import InvestigationService

router = APIRouter(prefix="/assistant", tags=["investigation assistant"])


@router.get("/status", response_model=AssistantStatus, summary="Get assistant status")
async def assistant_status() -> AssistantStatus:
    # No database or provider call is made: optional AI can never delay core pages.
    async with async_session_factory() as session:
        return InvestigationService(session).status()
