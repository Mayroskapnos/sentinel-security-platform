import asyncio
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.errors import ConflictError
from app.models.enums import ScenarioRunStatus
from app.models.scenario_run import ScenarioRun
from app.services import simulator as simulator_module
from app.services.simulator import ACTIVE_SLOT, ScenarioOrchestrator


@pytest.fixture
def enabled_settings() -> Settings:
    return Settings(
        sentinel_simulator_enabled=True,
        simulator_settle_seconds=0,
        simulator_scenario_timeout_seconds=30,
    )


@pytest.mark.asyncio
async def test_run_lifecycle_is_persistent(
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
    enabled_settings: Settings,
) -> None:
    monkeypatch.setattr(simulator_module, "get_settings", lambda: enabled_settings)
    orchestrator = ScenarioOrchestrator()
    orchestrator._validate_prerequisites = AsyncMock()  # type: ignore[method-assign]
    orchestrator.action_runner.execute = AsyncMock(return_value={"status": "completed"})
    broadcast = AsyncMock()
    monkeypatch.setattr(simulator_module.websocket_manager, "broadcast", broadcast)

    async with session_factory() as session:
        created = await orchestrator.start(session, "SCN-003")
        task = orchestrator._active_task
        assert created.status == ScenarioRunStatus.PENDING
        assert task is not None
        await task

    async with session_factory() as session:
        completed = await orchestrator.get_run(session, created.id)
        assert completed.status == ScenarioRunStatus.COMPLETED
        assert completed.current_step == 1
        assert completed.steps[0].status == "completed"
        assert completed.result["actions"][0]["action"] == "controlled_privileged_activity"
        assert [call.args[0].type for call in broadcast.await_args_list] == [
            "simulation_started",
            "simulation_step",
            "simulation_step",
            "simulation_finished",
        ]
        assert all(call.args[0].data.run_id == created.id for call in broadcast.await_args_list)


@pytest.mark.asyncio
async def test_cancellation_stops_future_steps_and_preserves_run(
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
    enabled_settings: Settings,
) -> None:
    monkeypatch.setattr(simulator_module, "get_settings", lambda: enabled_settings)
    orchestrator = ScenarioOrchestrator()
    orchestrator._validate_prerequisites = AsyncMock()  # type: ignore[method-assign]
    entered = asyncio.Event()

    async def blocked_action(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        entered.set()
        await asyncio.Future()

    orchestrator.action_runner.execute = blocked_action  # type: ignore[method-assign]

    async with session_factory() as session:
        created = await orchestrator.start(session, "SCN-005")
    await asyncio.wait_for(entered.wait(), timeout=2)

    async with session_factory() as session:
        cancelled = await orchestrator.cancel(session, created.id)
        assert cancelled.status == ScenarioRunStatus.CANCELLED
        assert cancelled.steps[0].status == "cancelled"
        assert all(step.status == "skipped" for step in cancelled.steps[1:])


@pytest.mark.asyncio
async def test_existing_active_run_rejects_concurrent_start(
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
    enabled_settings: Settings,
) -> None:
    monkeypatch.setattr(simulator_module, "get_settings", lambda: enabled_settings)
    async with session_factory() as session:
        session.add(
            ScenarioRun(
                scenario_id="SCN-001",
                scenario_name="SSH Credential Activity",
                status=ScenarioRunStatus.RUNNING,
                active_slot=ACTIVE_SLOT,
                current_step=1,
                total_steps=3,
                steps=[],
                expected_detections=[],
                targets=[],
                result={},
            )
        )
        await session.commit()

        with pytest.raises(ConflictError) as exc_info:
            await ScenarioOrchestrator().start(session, "SCN-003")
        assert exc_info.value.code == "SCENARIO_ALREADY_RUNNING"


@pytest.mark.asyncio
async def test_startup_marks_stale_run_failed_without_resuming(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        run = ScenarioRun(
            scenario_id="SCN-005",
            scenario_name="Multi-Stage Enterprise Security Exercise",
            status=ScenarioRunStatus.RUNNING,
            active_slot=ACTIVE_SLOT,
            current_step=2,
            total_steps=5,
            steps=[],
            expected_detections=[],
            targets=[],
            result={},
        )
        session.add(run)
        await session.commit()
        run_id = run.id

        recovered = await ScenarioOrchestrator().recover_stale(session)
        assert recovered == 1

    async with session_factory() as session:
        recovered_run = await session.get(ScenarioRun, run_id)
        assert recovered_run is not None
        assert recovered_run.status == ScenarioRunStatus.FAILED
        assert recovered_run.active_slot is None
        assert "not resumed" in (recovered_run.error_message or "")


@pytest.mark.asyncio
async def test_action_failure_clears_active_slot_and_skips_future_steps(
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
    enabled_settings: Settings,
) -> None:
    monkeypatch.setattr(simulator_module, "get_settings", lambda: enabled_settings)
    orchestrator = ScenarioOrchestrator()
    orchestrator._validate_prerequisites = AsyncMock()  # type: ignore[method-assign]
    orchestrator.action_runner.execute = AsyncMock(side_effect=RuntimeError("lab unavailable"))

    async with session_factory() as session:
        created = await orchestrator.start(session, "SCN-005")
        task = orchestrator._active_task
        assert task is not None
        await task

    async with session_factory() as session:
        failed = await orchestrator.get_run(session, created.id)
        model = await session.get(ScenarioRun, created.id)
        assert failed.status == ScenarioRunStatus.FAILED
        assert failed.steps[0].status == "failed"
        assert all(step.status == "skipped" for step in failed.steps[1:])
        assert model is not None
        assert model.active_slot is None
