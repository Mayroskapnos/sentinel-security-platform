"""Validate the local topology WebSocket path with one harmless lab event."""

import argparse
import asyncio
import json
import os
from datetime import UTC, datetime
from typing import Any

import httpx
import websockets


async def receive_status(url: str) -> str:
    async with websockets.connect(url) as socket:
        message = json.loads(await asyncio.wait_for(socket.recv(), timeout=5))
        return str(message.get("type"))


async def validate(base_url: str, collector_key: str) -> dict[str, Any]:
    websocket_url = base_url.replace("http://", "ws://").replace("https://", "wss://")
    websocket_url = f"{websocket_url.rstrip('/')}/api/v1/ws/events"
    first_connection = await receive_status(websocket_url)
    async with websockets.connect(websocket_url) as socket:
        reconnect_message = json.loads(await asyncio.wait_for(socket.recv(), timeout=5))
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event_type": "network_connection",
            "source": "network",
            "source_ip": "10.10.20.11",
            "destination_ip": "10.10.10.10",
            "destination_port": 8080,
            "hostname": "employee-02",
            "action": "connection_opened",
            "status": "success",
            "severity": "informational",
            "normalized_data": {"protocol": "tcp", "service": "http-alt"},
            "raw_event": {"validation": "milestone-6-websocket"},
        }
        async with httpx.AsyncClient(base_url=base_url, timeout=10) as client:
            response = await client.post(
                "/api/v1/telemetry/events",
                json=payload,
                headers={"X-Sentinel-Collector-Key": collector_key},
            )
            response.raise_for_status()
        message_types = [str(reconnect_message.get("type"))]
        update = None
        for _ in range(5):
            message = json.loads(await asyncio.wait_for(socket.recv(), timeout=5))
            message_types.append(str(message.get("type")))
            if message.get("type") == "network_connection_updated":
                update = message.get("data")
                break
    if first_connection != "telemetry_status" or message_types[0] != "telemetry_status":
        raise RuntimeError("WebSocket status was not delivered on connect and reconnect")
    if not isinstance(update, dict):
        raise TypeError("No network_connection_updated message was received")
    return {
        "initial_connection": first_connection,
        "reconnect_messages": message_types,
        "relationship_id": update.get("id"),
        "connection_count": update.get("connection_count"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--collector-key",
        default=os.getenv("COLLECTOR_API_KEY", "sentinel_local_collector_key_change_me"),
    )
    arguments = parser.parse_args()
    print(json.dumps(asyncio.run(validate(arguments.url, arguments.collector_key)), indent=2))


if __name__ == "__main__":
    main()
