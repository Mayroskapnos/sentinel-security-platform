import logging

from fastapi import WebSocket
from pydantic import BaseModel

from app.schemas.realtime import TelemetryStatusData, TelemetryStatusMessage

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manage event sockets for one backend process.

    Multi-instance deployments require shared pub/sub for cross-instance delivery.
    """

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    @property
    def connected_clients(self) -> int:
        return len(self._connections)

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)
        logger.info("websocket_connected clients=%d", self.connected_clients)
        await websocket.send_json(
            TelemetryStatusMessage(
                data=TelemetryStatusData(connected_clients=self.connected_clients)
            ).model_dump(mode="json")
        )

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self._connections:
            self._connections.remove(websocket)
            logger.info("websocket_disconnected clients=%d", self.connected_clients)

    async def broadcast(self, message: BaseModel) -> None:
        payload = message.model_dump(mode="json")
        failed: list[WebSocket] = []
        for connection in tuple(self._connections):
            try:
                await connection.send_json(payload)
            except Exception:
                failed.append(connection)
                logger.warning("websocket_broadcast_failed client_removed=true")
        for connection in failed:
            self.disconnect(connection)

    async def close_all(self) -> None:
        connections = tuple(self._connections)
        self._connections.clear()
        for connection in connections:
            try:
                await connection.close(code=1001)
            except Exception:
                logger.debug("websocket_close_failed", exc_info=True)


websocket_manager = WebSocketManager()
