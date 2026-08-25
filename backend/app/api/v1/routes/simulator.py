from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.simulator import (
    ScenarioDetail,
    ScenarioRunPage,
    ScenarioRunResponse,
    ScenarioSummary,
    SimulatorStatusResponse,
)
from app.services.simulator import scenario_orchestrator

router = APIRouter(prefix="/simulator", tags=["simulator"])
SessionDependency = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("/status", response_model=SimulatorStatusResponse, summary="Get simulator status")
async def simulator_status(session: SessionDependency) -> SimulatorStatusResponse:
    return await scenario_orchestrator.status(session)


@router.get("/scenarios", response_model=list[ScenarioSummary], summary="List controlled scenarios")
async def list_scenarios() -> list[ScenarioSummary]:
    return scenario_orchestrator.list_scenarios()


@router.get(
    "/scenarios/{scenario_id}",
    response_model=ScenarioDetail,
    summary="Get a controlled scenario",
)
async def get_scenario(scenario_id: str) -> ScenarioDetail:
    return scenario_orchestrator.get_scenario(scenario_id)


@router.post(
    "/run/{scenario_id}",
    response_model=ScenarioRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start a controlled scenario",
)
async def run_scenario(scenario_id: str, session: SessionDependency) -> ScenarioRunResponse:
    return await scenario_orchestrator.start(session, scenario_id)


@router.get("/runs", response_model=ScenarioRunPage, summary="List scenario run history")
async def list_runs(
    session: SessionDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ScenarioRunPage:
    return await scenario_orchestrator.list_runs(session, page=page, page_size=page_size)


@router.get("/runs/{run_id}", response_model=ScenarioRunResponse, summary="Get scenario run detail")
async def get_run(run_id: UUID, session: SessionDependency) -> ScenarioRunResponse:
    return await scenario_orchestrator.get_run(session, run_id)


@router.post(
    "/runs/{run_id}/cancel",
    response_model=ScenarioRunResponse,
    summary="Cancel future scenario steps",
)
async def cancel_run(run_id: UUID, session: SessionDependency) -> ScenarioRunResponse:
    return await scenario_orchestrator.cancel(session, run_id)
