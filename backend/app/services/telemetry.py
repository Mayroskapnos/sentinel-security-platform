import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.realtime.manager import WebSocketManager, websocket_manager
from app.schemas.security_event import SecurityEventCreate, SecurityEventResponse
from app.services.ingestion import EventIngestionService

logger = logging.getLogger(__name__)


class TelemetryIngestionService:
    def __init__(
        self,
        session: AsyncSession,
        manager: WebSocketManager = websocket_manager,
    ) -> None:
        self.ingestion_service = EventIngestionService(session, manager)
        self.manager = manager

    async def ingest(self, payload: SecurityEventCreate) -> SecurityEventResponse:
        try:
            event = await self.ingestion_service.ingest(payload)
        except Exception:
            logger.exception("telemetry_ingestion_failed")
            raise
        logger.info(
            "telemetry_ingested event_id=%s source=%s asset_resolved=%s",
            event.id,
            event.source,
            event.asset_id is not None,
        )
        return event
