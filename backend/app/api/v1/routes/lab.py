from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.lab import LabStatusResponse
from app.services.lab import LabStatusService

router = APIRouter(prefix="/lab", tags=["lab"])
SessionDependency = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("/status", response_model=LabStatusResponse, summary="Get corporate lab status")
async def get_lab_status(session: SessionDependency) -> LabStatusResponse:
    return await LabStatusService(session).get()
