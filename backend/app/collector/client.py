import asyncio
import logging

import httpx

from app.schemas.security_event import SecurityEventCreate

logger = logging.getLogger(__name__)


class TelemetryClient:
    def __init__(self, base_url: str, collector_key: str | None) -> None:
        self.endpoint = f"{base_url.rstrip('/')}/api/v1/telemetry/events"
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(10),
            headers={
                "User-Agent": "sentinel-lab-collector/0.1",
                **(
                    {"X-Sentinel-Collector-Key": collector_key} if collector_key is not None else {}
                ),
            },
        )

    async def send(self, event: SecurityEventCreate) -> None:
        delay = 1.0
        while True:
            try:
                response = await self.client.post(
                    self.endpoint,
                    json=event.model_dump(mode="json"),
                )
                response.raise_for_status()
                return
            except (httpx.HTTPError, OSError) as exc:
                logger.warning(
                    "collector_forward_retry delay_seconds=%.1f error_category=%s",
                    delay,
                    type(exc).__name__,
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, 30.0)

    async def close(self) -> None:
        await self.client.aclose()
