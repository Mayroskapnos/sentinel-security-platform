import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.realtime.manager import WebSocketManager, websocket_manager
from app.schemas.realtime import (
    AlertCreatedMessage,
    AlertUpdatedMessage,
    IncidentCreatedMessage,
    IncidentUpdatedMessage,
    NetworkConnectionUpdatedMessage,
    SecurityEventMessage,
)
from app.schemas.security_event import SecurityEventCreate, SecurityEventResponse
from app.services.correlation import CorrelationService
from app.services.detection import DetectionEngine
from app.services.events import SecurityEventService
from app.services.network import NetworkService

logger = logging.getLogger(__name__)


class EventIngestionService:
    """Persist, broadcast, then evaluate an event through one shared ingestion boundary."""

    def __init__(
        self,
        session: AsyncSession,
        manager: WebSocketManager = websocket_manager,
    ) -> None:
        self.session = session
        self.event_service = SecurityEventService(session)
        self.manager = manager

    async def ingest(self, payload: SecurityEventCreate) -> SecurityEventResponse:
        event = await self.event_service.create(payload)
        await self.manager.broadcast(SecurityEventMessage(data=event))
        try:
            connection = await NetworkService(self.session).aggregate_event(event.id)
            if connection:
                await self.manager.broadcast(NetworkConnectionUpdatedMessage(data=connection))
        except Exception:
            await self.session.rollback()
            logger.exception("network_aggregation_failed event_id=%s", event.id)
        try:
            results = await DetectionEngine(self.session).evaluate(event.id)
        except Exception:
            logger.exception("detection_evaluation_failed event_id=%s", event.id)
            return event
        for result in results:
            message = (
                AlertCreatedMessage(data=result.alert)
                if result.created
                else AlertUpdatedMessage(data=result.alert)
            )
            await self.manager.broadcast(message)
            try:
                outcome = await CorrelationService(self.session).process_alert(result.alert.id)
                incident_message = (
                    IncidentCreatedMessage(data=outcome.incident)
                    if outcome.created
                    else IncidentUpdatedMessage(data=outcome.incident)
                )
                await self.manager.broadcast(incident_message)
            except Exception:
                await self.session.rollback()
                logger.exception("incident_correlation_failed alert_id=%s", result.alert.id)
        return event
