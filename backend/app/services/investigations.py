import asyncio
import logging
import time
from datetime import UTC, datetime
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.errors import AppError, ConflictError, NotFoundError
from app.db.session import async_session_factory
from app.investigation.config import assistant_configuration
from app.investigation.grounding import (
    GroundingError,
    validate_analysis_output,
    validate_question_output,
)
from app.investigation.prompts import analysis_prompt, question_prompt
from app.investigation.providers import (
    InvestigationProvider,
    ProviderError,
    get_provider,
)
from app.investigation.rate_limit import assistant_rate_limiter
from app.investigation.redaction import redact_text, redact_value
from app.models.incident import Incident
from app.models.investigation import InvestigationAnalysis, InvestigationMessage
from app.realtime.manager import websocket_manager
from app.repositories.investigations import InvestigationRepository
from app.schemas.common import Page
from app.schemas.investigation import (
    AssistantStatus,
    InvestigationAnalysisListItem,
    InvestigationAnalysisResponse,
    InvestigationContext,
    InvestigationMessageResponse,
    InvestigationOutput,
    InvestigationQuestionResponse,
)
from app.schemas.realtime import (
    AnalysisCompletedMessage,
    AnalysisFailedMessage,
    AnalysisStartedMessage,
)
from app.services.investigation_context import InvestigationContextBuilder

logger = logging.getLogger(__name__)
analysis_request_lock = asyncio.Lock()


class InvestigationService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = InvestigationRepository(session)

    def status(self) -> AssistantStatus:
        return AssistantStatus.model_validate(assistant_configuration(self.settings).__dict__)

    async def request_analysis(self, incident_id: UUID) -> InvestigationAnalysisResponse:
        configuration = self._require_enabled()
        assistant_rate_limiter.check(f"analysis:{incident_id}", maximum=3, window_seconds=60)
        await self._require_incident(incident_id)
        async with analysis_request_lock:
            if await self.repository.active_analysis(incident_id):
                raise ConflictError(
                    "ANALYSIS_ALREADY_RUNNING",
                    "Only one Investigation Analysis may run for an Incident at a time.",
                )
            context, context_hash = await InvestigationContextBuilder(
                self.session, self.settings
            ).build(incident_id)
            analysis = InvestigationAnalysis(
                incident_id=incident_id,
                status="pending",
                provider=configuration.provider or "unknown",
                provider_label=configuration.provider_label,
                model=configuration.model or "unknown",
                analysis_version="1",
                context_hash=context_hash,
                context_snapshot=context.model_dump(mode="json"),
                observations=[],
                correlation_explanation={},
                key_assets=[],
                recommended_actions=[],
                uncertainties=[],
                raw_structured_result={},
            )
            self.session.add(analysis)
            try:
                await self.session.commit()
            except IntegrityError as exc:
                await self.session.rollback()
                raise ConflictError(
                    "ANALYSIS_ALREADY_RUNNING",
                    "Only one Investigation Analysis may run for an Incident at a time.",
                ) from exc
            await self.session.refresh(analysis)
            return self._analysis_response(analysis, context_hash)

    async def execute_analysis(
        self,
        analysis_id: UUID,
        provider: InvestigationProvider | None = None,
    ) -> InvestigationAnalysisResponse:
        analysis = await self.repository.get_analysis(analysis_id)
        if analysis is None:
            raise NotFoundError("ANALYSIS_NOT_FOUND", "Requested analysis does not exist.")
        if analysis.status != "pending":
            context_hash = (await self._current_context(analysis.incident_id))[1]
            return self._analysis_response(analysis, context_hash)
        started = time.perf_counter()
        analysis.status = "running"
        analysis.started_at = datetime.now(UTC)
        await self.session.commit()
        await websocket_manager.broadcast(AnalysisStartedMessage.from_analysis(analysis))
        context = InvestigationContext.model_validate(analysis.context_snapshot)
        try:
            selected_provider = provider or get_provider(self.settings)
            result = await asyncio.wait_for(
                selected_provider.analyze_incident(context, analysis_prompt(context)),
                timeout=self.settings.sentinel_ai_timeout_seconds,
            )
            output = validate_analysis_output(result.output, context)
            analysis.status = "completed"
            analysis.completed_at = datetime.now(UTC)
            analysis.executive_summary = output.executive_summary
            analysis.observations = [item.model_dump(mode="json") for item in output.observations]
            analysis.correlation_explanation = output.correlation_explanation.model_dump(
                mode="json"
            )
            analysis.key_assets = [item.model_dump(mode="json") for item in output.key_assets]
            analysis.uncertainties = [item.model_dump(mode="json") for item in output.uncertainties]
            analysis.recommended_actions = [
                item.model_dump(mode="json") for item in output.recommended_actions
            ]
            analysis.raw_structured_result = output.model_dump(mode="json")
            analysis.input_tokens = result.usage.input_tokens
            analysis.output_tokens = result.usage.output_tokens
            analysis.error_message = None
            await self.session.commit()
            await self.session.refresh(analysis)
            current_hash = (await self._current_context(analysis.incident_id))[1]
            response = self._analysis_response(analysis, current_hash)
            await websocket_manager.broadcast(AnalysisCompletedMessage.from_analysis(analysis))
            logger.info(
                "investigation_analysis_completed analysis_id=%s incident_id=%s "
                "provider=%s model=%s duration_ms=%.2f",
                analysis.id,
                analysis.incident_id,
                analysis.provider,
                analysis.model,
                (time.perf_counter() - started) * 1000,
            )
            return response
        except (TimeoutError, ProviderError, GroundingError, ValidationError) as exc:
            await self.session.rollback()
            analysis = await self.repository.get_analysis(analysis_id)
            assert analysis is not None
            analysis.status = "failed"
            analysis.completed_at = datetime.now(UTC)
            analysis.error_message = self._safe_failure(exc)
            await self.session.commit()
            await self.session.refresh(analysis)
            current_hash = (await self._current_context(analysis.incident_id))[1]
            response = self._analysis_response(analysis, current_hash)
            await websocket_manager.broadcast(AnalysisFailedMessage.from_analysis(analysis))
            logger.warning(
                "investigation_analysis_failed analysis_id=%s incident_id=%s "
                "provider=%s model=%s duration_ms=%.2f category=%s",
                analysis.id,
                analysis.incident_id,
                analysis.provider,
                analysis.model,
                (time.perf_counter() - started) * 1000,
                type(exc).__name__,
            )
            return response
        except Exception:
            await self.session.rollback()
            analysis = await self.repository.get_analysis(analysis_id)
            assert analysis is not None
            analysis.status = "failed"
            analysis.completed_at = datetime.now(UTC)
            analysis.error_message = "The Investigation Assistant failed safely."
            await self.session.commit()
            await self.session.refresh(analysis)
            await websocket_manager.broadcast(AnalysisFailedMessage.from_analysis(analysis))
            logger.exception(
                "investigation_analysis_unexpected_failure analysis_id=%s incident_id=%s",
                analysis.id,
                analysis.incident_id,
            )
            current_hash = (await self._current_context(analysis.incident_id))[1]
            return self._analysis_response(analysis, current_hash)

    async def latest_analysis(self, incident_id: UUID) -> InvestigationAnalysisResponse | None:
        await self._require_incident(incident_id)
        analysis = await self.repository.latest_analysis(incident_id)
        if analysis is None:
            return None
        current_hash = (await self._current_context(incident_id))[1]
        return self._analysis_response(analysis, current_hash)

    async def get_analysis(
        self, incident_id: UUID, analysis_id: UUID
    ) -> InvestigationAnalysisResponse:
        analysis = await self.repository.get_analysis(analysis_id, incident_id)
        if analysis is None:
            raise NotFoundError("ANALYSIS_NOT_FOUND", "Requested analysis does not exist.")
        current_hash = (await self._current_context(incident_id))[1]
        return self._analysis_response(analysis, current_hash)

    async def list_analyses(
        self, incident_id: UUID, page: int, page_size: int
    ) -> Page[InvestigationAnalysisListItem]:
        await self._require_incident(incident_id)
        current_hash = (await self._current_context(incident_id))[1]
        rows, total = await self.repository.list_analyses(incident_id, page, page_size)
        return Page[InvestigationAnalysisListItem].create(
            items=[self._analysis_list_item(row, current_hash) for row in rows],
            page=page,
            page_size=page_size,
            total=total,
        )

    async def messages(
        self, incident_id: UUID, limit: int = 20
    ) -> list[InvestigationMessageResponse]:
        await self._require_incident(incident_id)
        return [
            InvestigationMessageResponse.model_validate(message, from_attributes=True)
            for message in await self.repository.recent_messages(incident_id, limit)
        ]

    async def answer_question(
        self,
        incident_id: UUID,
        question: str,
        provider: InvestigationProvider | None = None,
    ) -> InvestigationQuestionResponse:
        configuration = self._require_enabled()
        assistant_rate_limiter.check(f"question:{incident_id}", maximum=10, window_seconds=60)
        await self._require_incident(incident_id)
        context, context_hash = await self._current_context(incident_id)
        recent = await self.repository.recent_messages(
            incident_id, self.settings.sentinel_ai_question_history
        )
        bounded_history = [
            {"role": item.role, "content": redact_text(item.content)[:1_000]} for item in recent
        ]
        safe_question = redact_text(question)
        current_analysis = await self.repository.latest_current_completed(incident_id, context_hash)
        current_analysis_context = (
            redact_value(current_analysis.raw_structured_result) if current_analysis else None
        )
        selected_provider = provider or get_provider(self.settings)
        try:
            result = await asyncio.wait_for(
                selected_provider.answer_question(
                    context,
                    safe_question,
                    bounded_history,
                    question_prompt(
                        context,
                        safe_question,
                        bounded_history,
                        current_analysis_context,
                    ),
                ),
                timeout=self.settings.sentinel_ai_timeout_seconds,
            )
            output = validate_question_output(result.output, context)
        except (TimeoutError, ProviderError, GroundingError, ValidationError) as exc:
            raise AppError("ASSISTANT_QUESTION_FAILED", self._safe_failure(exc), 502) from exc
        question_model = InvestigationMessage(
            incident_id=incident_id,
            analysis_id=current_analysis.id if current_analysis else None,
            role="user",
            content=safe_question,
            evidence_refs=[],
            context_hash=context_hash,
            provider=None,
            model=None,
        )
        self.session.add(question_model)
        await self.session.flush()
        answer_model = InvestigationMessage(
            incident_id=incident_id,
            analysis_id=current_analysis.id if current_analysis else None,
            reply_to_id=question_model.id,
            role="assistant",
            content=output.answer,
            evidence_refs=output.evidence_refs,
            context_hash=context_hash,
            provider=configuration.provider,
            model=configuration.model,
        )
        self.session.add(answer_model)
        await self.session.commit()
        await self.session.refresh(question_model)
        await self.session.refresh(answer_model)
        return InvestigationQuestionResponse(
            question=InvestigationMessageResponse.model_validate(
                question_model, from_attributes=True
            ),
            answer=InvestigationMessageResponse.model_validate(answer_model, from_attributes=True),
            evidence_catalog=context.evidence_catalog,
        )

    async def _require_incident(self, incident_id: UUID) -> Incident:
        incident = await self.session.get(Incident, incident_id)
        if incident is None:
            raise NotFoundError("INCIDENT_NOT_FOUND", "Requested incident does not exist.")
        return incident

    def _require_enabled(self):  # noqa: ANN202
        configuration = assistant_configuration(self.settings)
        if not configuration.enabled:
            code = (
                "AI_ASSISTANT_DISABLED"
                if configuration.mode == "disabled"
                else "AI_ASSISTANT_UNAVAILABLE"
            )
            raise AppError(code, configuration.message, 503)
        return configuration

    async def _current_context(self, incident_id: UUID) -> tuple[InvestigationContext, str]:
        return await InvestigationContextBuilder(self.session, self.settings).build(incident_id)

    @staticmethod
    def _analysis_list_item(
        analysis: InvestigationAnalysis, current_hash: str
    ) -> InvestigationAnalysisListItem:
        return InvestigationAnalysisListItem(
            id=analysis.id,
            incident_id=analysis.incident_id,
            status=analysis.status,
            provider=analysis.provider,
            provider_label=analysis.provider_label,
            model=analysis.model,
            requested_at=analysis.requested_at,
            started_at=analysis.started_at,
            completed_at=analysis.completed_at,
            analysis_version=analysis.analysis_version,
            context_hash=analysis.context_hash,
            is_stale=analysis.context_hash != current_hash,
            input_tokens=analysis.input_tokens,
            output_tokens=analysis.output_tokens,
            error_message=analysis.error_message,
            created_at=analysis.created_at,
            updated_at=analysis.updated_at,
        )

    @classmethod
    def _analysis_response(
        cls, analysis: InvestigationAnalysis, current_hash: str
    ) -> InvestigationAnalysisResponse:
        output = None
        if analysis.status == "completed":
            output = InvestigationOutput.model_validate(
                {
                    "executive_summary": analysis.executive_summary,
                    "observations": analysis.observations,
                    "correlation_explanation": analysis.correlation_explanation,
                    "key_assets": analysis.key_assets,
                    "uncertainties": analysis.uncertainties,
                    "recommended_actions": analysis.recommended_actions,
                }
            )
        context = InvestigationContext.model_validate(analysis.context_snapshot)
        return InvestigationAnalysisResponse(
            **cls._analysis_list_item(analysis, current_hash).model_dump(),
            output=output,
            evidence_catalog=context.evidence_catalog,
        )

    @staticmethod
    def _safe_failure(exc: Exception) -> str:
        if isinstance(exc, TimeoutError):
            return "The Investigation Assistant timed out before completing analysis."
        if isinstance(exc, (ProviderError, GroundingError)):
            return str(exc)[:2_000]
        return "The Investigation Assistant returned invalid structured output."

    @staticmethod
    async def recover_interrupted(session: AsyncSession) -> int:
        completed_at = datetime.now(UTC)
        result = await session.execute(
            update(InvestigationAnalysis)
            .where(InvestigationAnalysis.status.in_(("pending", "running")))
            .values(
                status="failed",
                completed_at=completed_at,
                error_message="Backend restarted before analysis completed. Regenerate explicitly.",
            )
        )
        await session.commit()
        return int(result.rowcount or 0)


async def run_analysis_task(analysis_id: UUID) -> None:
    async with async_session_factory() as session:
        await InvestigationService(session).execute_analysis(analysis_id)
