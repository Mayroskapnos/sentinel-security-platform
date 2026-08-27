from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.realtime.manager import websocket_manager
from app.schemas.common import Page
from app.schemas.incident import IncidentDetail, IncidentFilters, IncidentListItem, IncidentUpdate
from app.schemas.investigation import (
    InvestigationAnalysisListItem,
    InvestigationAnalysisResponse,
    InvestigationMessageResponse,
    InvestigationQuestionRequest,
    InvestigationQuestionResponse,
)
from app.schemas.realtime import IncidentUpdatedMessage
from app.services.incidents import IncidentService
from app.services.investigations import InvestigationService, run_analysis_task

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


@router.post(
    "/{incident_id}/analysis",
    response_model=InvestigationAnalysisResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate an Incident investigation analysis",
)
async def generate_analysis(
    incident_id: UUID,
    background_tasks: BackgroundTasks,
    session: SessionDependency,
) -> InvestigationAnalysisResponse:
    analysis = await InvestigationService(session).request_analysis(incident_id)
    background_tasks.add_task(run_analysis_task, analysis.id)
    return analysis


@router.get(
    "/{incident_id}/analysis",
    response_model=InvestigationAnalysisResponse | None,
    summary="Get the latest Incident analysis",
)
async def get_latest_analysis(
    incident_id: UUID, session: SessionDependency
) -> InvestigationAnalysisResponse | None:
    return await InvestigationService(session).latest_analysis(incident_id)


@router.get(
    "/{incident_id}/analysis/{analysis_id}",
    response_model=InvestigationAnalysisResponse,
    summary="Get a persisted Incident analysis",
)
async def get_analysis(
    incident_id: UUID, analysis_id: UUID, session: SessionDependency
) -> InvestigationAnalysisResponse:
    return await InvestigationService(session).get_analysis(incident_id, analysis_id)


@router.get(
    "/{incident_id}/analyses",
    response_model=Page[InvestigationAnalysisListItem],
    summary="List Incident analysis history",
)
async def list_analyses(
    incident_id: UUID,
    session: SessionDependency,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[InvestigationAnalysisListItem]:
    return await InvestigationService(session).list_analyses(incident_id, page, page_size)


@router.get(
    "/{incident_id}/assistant/messages",
    response_model=list[InvestigationMessageResponse],
    summary="List bounded Incident assistant history",
)
async def list_assistant_messages(
    incident_id: UUID,
    session: SessionDependency,
    limit: int = Query(default=20, ge=1, le=50),
) -> list[InvestigationMessageResponse]:
    return await InvestigationService(session).messages(incident_id, limit)


@router.post(
    "/{incident_id}/assistant/questions",
    response_model=InvestigationQuestionResponse,
    summary="Ask a bounded question about an Incident",
)
async def ask_incident_question(
    incident_id: UUID,
    payload: InvestigationQuestionRequest,
    session: SessionDependency,
) -> InvestigationQuestionResponse:
    return await InvestigationService(session).answer_question(incident_id, payload.question)
