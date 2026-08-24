from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app
from app.realtime.manager import websocket_manager


def test_websocket_client_connects_and_disconnects() -> None:
    with TestClient(app) as client:
        with client.websocket_connect("/api/v1/ws/events") as websocket:
            message = websocket.receive_json()
            assert message["version"] == "1"
            assert message["type"] == "telemetry_status"
            assert message["data"]["status"] == "connected"
        assert websocket_manager.connected_clients == 0


def test_websocket_rejects_untrusted_browser_origin() -> None:
    with TestClient(app) as client:
        try:
            with client.websocket_connect(
                "/api/v1/ws/events", headers={"origin": "https://untrusted.example"}
            ):
                raise AssertionError("untrusted origin connected")
        except WebSocketDisconnect as exc:
            assert exc.code == 1008
