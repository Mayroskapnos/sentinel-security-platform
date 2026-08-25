import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.realtime.manager import WebSocketManager, websocket_manager
from app.schemas.realtime import AlertCreatedMessage, AlertUpdatedMessage, SecurityEventMessage
from app.schemas.security_event import SecurityEventCreate, SecurityEventResponse
from app.services.detection import DetectionEngine
from app.services.events import SecurityEventService

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
        return event
