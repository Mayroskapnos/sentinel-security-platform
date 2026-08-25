import asyncio
import logging
import math
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import status
from sqlalchemy import distinct, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.core.errors import AppError, ConflictError, NotFoundError
from app.models.alert import Alert, AlertEvent
from app.models.detection_rule import DetectionRule
from app.models.enums import ScenarioRunStatus, ScenarioStepStatus
from app.models.scenario_run import ScenarioRun
from app.models.security_event import SecurityEvent
from app.realtime.manager import websocket_manager
from app.schemas.realtime import (
    SimulationCancelledMessage,
    SimulationFailedMessage,
    SimulationFinishedMessage,
    SimulationStartedMessage,
    SimulationStepMessage,
)
from app.schemas.simulator import (
    DetectionObservation,
    ScenarioAlertReference,
    ScenarioDetail,
    ScenarioRunPage,
    ScenarioRunResponse,
    ScenarioRunStep,
    ScenarioSummary,
    SimulatorStatusResponse,
)
from app.services.lab import LabStatusService
from app.simulator.actions import SafeActionRunner
from app.simulator.loader import ScenarioLoader

logger = logging.getLogger(__name__)
ACTIVE_SLOT = "corporate-lab"
ACTIVE_STATUSES = (ScenarioRunStatus.PENDING, ScenarioRunStatus.RUNNING)


class ScenarioOrchestrator:
    def __init__(self) -> None:
        self.loader = ScenarioLoader()
        self.action_runner = SafeActionRunner()
        self._active_task: asyncio.Task[None] | None = None
        self._active_run_id: UUID | None = None
        self._cancel_requested: set[UUID] = set()

    def list_scenarios(self) -> list[ScenarioSummary]:
        return self.loader.summaries()

    def get_scenario(self, scenario_id: str) -> ScenarioDetail:
        scenario = self.loader.by_id(scenario_id)
        if scenario is None:
            raise NotFoundError("SCENARIO_NOT_FOUND", "Requested scenario does not exist.")
        return self.loader.detail(scenario)

    async def start(self, session: AsyncSession, scenario_id: str) -> ScenarioRunResponse:
        settings = get_settings()
        if not settings.sentinel_simulator_enabled:
            raise AppError(
                "SIMULATOR_DISABLED",
                "The controlled Attack Simulator is disabled by configuration.",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        scenario = self.loader.by_id(scenario_id)
        if scenario is None:
            raise NotFoundError("SCENARIO_NOT_FOUND", "Requested scenario does not exist.")
        await self._validate_prerequisites(session, scenario.targets, scenario.expected_detections)

        steps = [
            ScenarioRunStep(
                index=index,
                name=step.name,
                action=step.action,
                status=ScenarioStepStatus.PENDING,
            ).model_dump(mode="json")
            for index, step in enumerate(scenario.steps, 1)
        ]
        run = ScenarioRun(
            scenario_id=scenario.id,
            scenario_name=scenario.name,
            status=ScenarioRunStatus.PENDING,
            active_slot=ACTIVE_SLOT,
            current_step=0,
            total_steps=len(scenario.steps),
            requested_by="local-user",
            steps=steps,
            expected_detections=scenario.expected_detections,
            targets=scenario.targets,
            result={
                "suppression_advisories": await self._suppression_advisories(session, scenario)
            },
        )
        session.add(run)
        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise ConflictError(
                "SCENARIO_ALREADY_RUNNING",
                "Another Corporate Lab scenario is already active.",
            ) from exc
        await session.refresh(run)

        factory = async_sessionmaker(session.bind, expire_on_commit=False)
        self._active_run_id = run.id
        self._active_task = asyncio.create_task(
            self._execute(factory, run.id, scenario.id), name=f"scenario-{run.id}"
        )
        return await self._response(session, run)

    async def list_runs(
        self, session: AsyncSession, *, page: int, page_size: int
    ) -> ScenarioRunPage:
        total = int(await session.scalar(select(func.count()).select_from(ScenarioRun)) or 0)
        runs = list(
            await session.scalars(
                select(ScenarioRun)
                .order_by(ScenarioRun.created_at.desc(), ScenarioRun.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return ScenarioRunPage(
            items=[await self._response(session, run) for run in runs],
            page=page,
            page_size=page_size,
            total=total,
            pages=math.ceil(total / page_size) if total else 0,
        )

    async def get_run(self, session: AsyncSession, run_id: UUID) -> ScenarioRunResponse:
        run = await session.get(ScenarioRun, run_id)
        if run is None:
            raise NotFoundError("SCENARIO_RUN_NOT_FOUND", "Requested scenario run does not exist.")
        return await self._response(session, run)

    async def cancel(self, session: AsyncSession, run_id: UUID) -> ScenarioRunResponse:
        run = await session.get(ScenarioRun, run_id)
        if run is None:
            raise NotFoundError("SCENARIO_RUN_NOT_FOUND", "Requested scenario run does not exist.")
        if run.status not in ACTIVE_STATUSES:
            raise ConflictError(
                "SCENARIO_NOT_ACTIVE", "Only an active scenario run can be cancelled."
            )
        if self._active_run_id != run_id or self._active_task is None:
            raise ConflictError(
                "SCENARIO_NOT_OWNED",
                "The active run is not owned by this backend process and cannot be resumed.",
            )
        self._cancel_requested.add(run_id)
        self._active_task.cancel()
        await asyncio.gather(self._active_task, return_exceptions=True)
        await session.refresh(run)
        return await self._response(session, run)

    async def status(self, session: AsyncSession) -> SimulatorStatusResponse:
        enabled = get_settings().sentinel_simulator_enabled
        active = await session.scalar(
            select(ScenarioRun)
            .where(ScenarioRun.status.in_(ACTIVE_STATUSES))
            .order_by(ScenarioRun.created_at.desc())
        )
        if not enabled:
            return SimulatorStatusResponse(
                enabled=False,
                available=False,
                state="disabled",
                message="Simulator execution is disabled; scenario history remains available.",
            )
        if active is not None:
            return SimulatorStatusResponse(
                enabled=True,
                available=True,
                state="running",
                active_run=await self._response(session, active),
                message=f"Running {active.scenario_id}.",
            )
        available = await self.action_runner.health()
        return SimulatorStatusResponse(
            enabled=True,
            available=available,
            state="idle" if available else "unavailable",
            message=(
                "Controlled simulator is ready."
                if available
                else "The internal simulator broker is unavailable."
            ),
        )

    async def recover_stale(self, session: AsyncSession) -> int:
        now = datetime.now(UTC)
        result = await session.execute(
            update(ScenarioRun)
            .where(ScenarioRun.status.in_(ACTIVE_STATUSES))
            .values(
                status=ScenarioRunStatus.FAILED,
                active_slot=None,
                finished_at=now,
                error_message="Backend restart interrupted this run; it was not resumed.",
            )
        )
        await session.commit()
        return int(result.rowcount or 0)

    async def shutdown(self) -> None:
        if self._active_task and not self._active_task.done():
            self._active_task.cancel()
            await asyncio.gather(self._active_task, return_exceptions=True)

    async def _validate_prerequisites(
        self, session: AsyncSession, targets: list[str], expected_detections: list[str]
    ) -> None:
        active = await session.scalar(
            select(ScenarioRun.id).where(ScenarioRun.status.in_(ACTIVE_STATUSES))
        )
        if active is not None:
            raise ConflictError(
                "SCENARIO_ALREADY_RUNNING", "Another Corporate Lab scenario is already active."
            )
        lab = await LabStatusService(session).get()
        online = {asset.hostname for asset in lab.assets if asset.status == "online"}
        missing_assets = sorted(set(targets) - online)
        if lab.collector_status != "active" or missing_assets:
            detail = (
                f" Offline required assets: {', '.join(missing_assets)}." if missing_assets else ""
            )
            raise AppError(
                "SIMULATOR_LAB_UNAVAILABLE",
                f"Corporate Lab and collector must be healthy before a run.{detail}",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        enabled_rules = set(
            await session.scalars(
                select(DetectionRule.rule_id).where(
                    DetectionRule.rule_id.in_(expected_detections), DetectionRule.enabled.is_(True)
                )
            )
        )
        missing_rules = sorted(set(expected_detections) - enabled_rules)
        if missing_rules:
            raise AppError(
                "SIMULATOR_RULES_UNAVAILABLE",
                f"Required detection rules are missing or disabled: {', '.join(missing_rules)}.",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        if not await self.action_runner.health():
            raise AppError(
                "SIMULATOR_BROKER_UNAVAILABLE",
                "The fixed internal simulator broker is unavailable.",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )

    async def _execute(
        self,
        factory: async_sessionmaker[AsyncSession],
        run_id: UUID,
        scenario_id: str,
    ) -> None:
        scenario = self.loader.by_id(scenario_id)
        if scenario is None:
            return
        try:
            async with asyncio.timeout(get_settings().simulator_scenario_timeout_seconds):
                async with factory() as session:
                    run = await session.get(ScenarioRun, run_id)
                    if run is None:
                        return
                    run.status = ScenarioRunStatus.RUNNING
                    run.started_at = datetime.now(UTC)
                    await session.commit()
                    await websocket_manager.broadcast(SimulationStartedMessage.from_run(run))

                action_results = []
                for index, step in enumerate(scenario.steps, 1):
                    await self._update_step(
                        factory, run_id, index, ScenarioStepStatus.RUNNING, "Action started."
                    )
                    if step.action == "wait":
                        await asyncio.sleep(step.seconds or 1)
                        result = {"status": "completed", "wait_seconds": step.seconds}
                    else:
                        result = await self.action_runner.execute(
                            step, run_id=str(run_id), scenario_id=scenario_id
                        )
                    action_results.append({"step": index, "action": step.action, "result": result})
                    await self._update_step(
                        factory,
                        run_id,
                        index,
                        ScenarioStepStatus.COMPLETED,
                        "Controlled lab action completed.",
                    )

                if get_settings().simulator_settle_seconds:
                    await asyncio.sleep(get_settings().simulator_settle_seconds)
                async with factory() as session:
                    run = await session.get(ScenarioRun, run_id)
                    if run is None:
                        return
                    run.status = ScenarioRunStatus.COMPLETED
                    run.finished_at = datetime.now(UTC)
                    run.active_slot = None
                    run.result = {**run.result, "actions": action_results}
                    await session.commit()
                    await websocket_manager.broadcast(SimulationFinishedMessage.from_run(run))
        except asyncio.CancelledError:
            cancelled = run_id in self._cancel_requested
            await self._finalize_failure(
                factory,
                run_id,
                ScenarioRunStatus.CANCELLED if cancelled else ScenarioRunStatus.FAILED,
                (
                    "Cancelled by the user; generated telemetry and alerts were preserved."
                    if cancelled
                    else "Backend shutdown interrupted this run; it was not resumed."
                ),
            )
        except Exception as exc:
            logger.exception("scenario_execution_failed run_id=%s", run_id)
            await self._finalize_failure(factory, run_id, ScenarioRunStatus.FAILED, str(exc)[:2000])
        finally:
            self._cancel_requested.discard(run_id)
            if self._active_run_id == run_id:
                self._active_run_id = None
                self._active_task = None

    async def _update_step(
        self,
        factory: async_sessionmaker[AsyncSession],
        run_id: UUID,
        index: int,
        step_status: ScenarioStepStatus,
        message: str,
    ) -> None:
        async with factory() as session:
            run = await session.get(ScenarioRun, run_id)
            if run is None:
                return
            now = datetime.now(UTC)
            steps = [dict(item) for item in run.steps]
            item = steps[index - 1]
            item["status"] = step_status
            item["message"] = message
            if step_status == ScenarioStepStatus.RUNNING:
                item["started_at"] = now.isoformat()
                run.current_step = index
            else:
                item["finished_at"] = now.isoformat()
            run.steps = steps
            await session.commit()
            await websocket_manager.broadcast(SimulationStepMessage.from_run(run, item))

    async def _finalize_failure(
        self,
        factory: async_sessionmaker[AsyncSession],
        run_id: UUID,
        run_status: ScenarioRunStatus,
        message: str,
    ) -> None:
        async with factory() as session:
            run = await session.get(ScenarioRun, run_id)
            if run is None:
                return
            now = datetime.now(UTC)
            steps = [dict(item) for item in run.steps]
            if run.current_step and steps[run.current_step - 1]["status"] == "running":
                current = steps[run.current_step - 1]
                current["status"] = (
                    ScenarioStepStatus.CANCELLED
                    if run_status == ScenarioRunStatus.CANCELLED
                    else ScenarioStepStatus.FAILED
                )
                current["finished_at"] = now.isoformat()
                current["message"] = message
            for item in steps[run.current_step :]:
                item["status"] = ScenarioStepStatus.SKIPPED
                item["message"] = "Not executed."
            run.steps = steps
            run.status = run_status
            run.active_slot = None
            run.finished_at = now
            run.error_message = message
            await session.commit()
            websocket_message = (
                SimulationCancelledMessage.from_run(run)
                if run_status == ScenarioRunStatus.CANCELLED
                else SimulationFailedMessage.from_run(run)
            )
            await websocket_manager.broadcast(websocket_message)

    async def _response(self, session: AsyncSession, run: ScenarioRun) -> ScenarioRunResponse:
        event_count = int(
            await session.scalar(
                select(func.count(SecurityEvent.id)).where(SecurityEvent.scenario_run_id == run.id)
            )
            or 0
        )
        rows = (
            await session.execute(
                select(
                    distinct(Alert.id),
                    DetectionRule.rule_id,
                    Alert.title,
                    Alert.severity,
                    Alert.timestamp,
                )
                .join(AlertEvent, AlertEvent.alert_id == Alert.id)
                .join(SecurityEvent, SecurityEvent.id == AlertEvent.event_id)
                .join(DetectionRule, DetectionRule.id == Alert.detection_rule_id)
                .where(SecurityEvent.scenario_run_id == run.id)
                .order_by(Alert.timestamp)
            )
        ).all()
        alerts = [
            ScenarioAlertReference(
                id=row[0], rule_id=row[1], title=row[2], severity=row[3], timestamp=row[4]
            )
            for row in rows
        ]
        detections = [
            DetectionObservation(
                rule_id=rule_id,
                observed=any(alert.rule_id == rule_id for alert in alerts),
                alert_ids=[alert.id for alert in alerts if alert.rule_id == rule_id],
                note=(
                    None
                    if any(alert.rule_id == rule_id for alert in alerts)
                    else (
                        "Expected but not observed; alert suppression or collection timing may "
                        "apply."
                    )
                ),
            )
            for rule_id in run.expected_detections
        ]
        response = ScenarioRunResponse.model_validate(run)
        return response.model_copy(
            update={
                "event_count": event_count,
                "alert_count": len(alerts),
                "detections": detections,
                "alerts": alerts,
            },
        )

    async def _suppression_advisories(self, session: AsyncSession, scenario) -> list[dict]:
        advisories = []
        rules = list(
            await session.scalars(
                select(DetectionRule).where(DetectionRule.rule_id.in_(scenario.expected_detections))
            )
        )
        now = datetime.now(UTC)
        for rule in rules:
            suppression = int(rule.configuration.get("suppression_seconds", 0))
            latest = await session.scalar(
                select(func.max(Alert.timestamp)).where(Alert.detection_rule_id == rule.id)
            )
            if suppression and latest:
                retry_at = latest + timedelta(seconds=suppression)
                if retry_at > now:
                    advisories.append(
                        {"rule_id": rule.rule_id, "recommended_retry_at": retry_at.isoformat()}
                    )
        return advisories


scenario_orchestrator = ScenarioOrchestrator()
