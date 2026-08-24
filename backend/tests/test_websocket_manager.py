from unittest.mock import AsyncMock

import pytest

from app.realtime.manager import WebSocketManager
from app.schemas.realtime import TelemetryStatusData, TelemetryStatusMessage


class FakeWebSocket:
    def __init__(self, fail_after: int | None = None) -> None:
        self.accept = AsyncMock()
        self.close = AsyncMock()
        self.messages: list[dict] = []
        self.fail_after = fail_after

    async def send_json(self, payload: dict) -> None:
        if self.fail_after is not None and len(self.messages) >= self.fail_after:
            raise RuntimeError("client disconnected")
        self.messages.append(payload)


@pytest.mark.asyncio
async def test_multiple_clients_receive_broadcast_and_disconnect_cleanly() -> None:
    manager = WebSocketManager()
    first = FakeWebSocket()
    second = FakeWebSocket()
    await manager.connect(first)
    await manager.connect(second)

    message = TelemetryStatusMessage(data=TelemetryStatusData(connected_clients=2))
    await manager.broadcast(message)

    assert first.messages[-1]["type"] == "telemetry_status"
    assert second.messages[-1]["type"] == "telemetry_status"
    manager.disconnect(first)
    manager.disconnect(second)
    assert manager.connected_clients == 0


@pytest.mark.asyncio
async def test_failed_client_does_not_block_healthy_client() -> None:
    manager = WebSocketManager()
    broken = FakeWebSocket(fail_after=1)
    healthy = FakeWebSocket()
    await manager.connect(broken)
    await manager.connect(healthy)

    message = TelemetryStatusMessage(data=TelemetryStatusData(connected_clients=2))
    await manager.broadcast(message)

    assert healthy.messages[-1]["type"] == "telemetry_status"
    assert manager.connected_clients == 1
