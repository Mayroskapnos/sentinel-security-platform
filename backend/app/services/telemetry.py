import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.realtime.manager import WebSocketManager, websocket_manager
from app.schemas.realtime import SecurityEventMessage
from app.schemas.security_event import SecurityEventCreate, SecurityEventResponse
from app.services.events import SecurityEventService

logger = logging.getLogger(__name__)


class TelemetryIngestionService:
    def __init__(
        self,
        session: AsyncSession,
        manager: WebSocketManager = websocket_manager,
    ) -> None:
        self.event_service = SecurityEventService(session)
        self.manager = manager

    async def ingest(self, payload: SecurityEventCreate) -> SecurityEventResponse:
        try:
            event = await self.event_service.create(payload)
        except Exception:
            logger.exception("telemetry_ingestion_failed")
            raise
        logger.info(
            "telemetry_ingested event_id=%s source=%s asset_resolved=%s",
            event.id,
            event.source,
            event.asset_id is not None,
        )
        await self.manager.broadcast(SecurityEventMessage(data=event))
        return event
