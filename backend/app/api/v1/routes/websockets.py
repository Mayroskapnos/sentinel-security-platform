import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.core.config import get_settings
from app.realtime.manager import websocket_manager

router = APIRouter(tags=["telemetry"])
logger = logging.getLogger(__name__)


@router.websocket("/ws/events")
async def event_websocket(websocket: WebSocket) -> None:
    origin = websocket.headers.get("origin")
    if origin and origin not in get_settings().websocket_origins:
        logger.warning("websocket_origin_rejected")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        await websocket_manager.connect(websocket)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        websocket_manager.disconnect(websocket)
