import asyncio
import logging
import os
from contextlib import suppress
from pathlib import Path

from app.collector.checkpoint import CheckpointStore, fingerprint
from app.collector.client import TelemetryClient
from app.collector.registry import Source, sources
from app.core.logging import configure_logging

logger = logging.getLogger(__name__)


class Collector:
    def __init__(self) -> None:
        log_root = Path(os.getenv("LAB_LOG_ROOT", "/logs"))
        state_root = Path(os.getenv("COLLECTOR_STATE_ROOT", "/var/lib/sentinel-collector"))
        self.source_definitions = sources(log_root)
        self.checkpoints = CheckpointStore(state_root / "checkpoints.json")
        self.health_path = state_root / "healthy"
        self.client = TelemetryClient(
            os.getenv("SENTINEL_URL", "http://backend:8000"),
            os.getenv("COLLECTOR_API_KEY"),
        )

    async def run(self) -> None:
        logger.info("collector_started source_count=%d", len(self.source_definitions))
        for source in self.source_definitions:
            logger.info("collector_source_registered source=%s path=%s", source.name, source.path)
        try:
            async with asyncio.TaskGroup() as group:
                group.create_task(self._heartbeat())
                for source in self.source_definitions:
                    group.create_task(self._follow(source))
        finally:
            await self.client.close()
            logger.info("collector_stopped")

    async def _heartbeat(self) -> None:
        while True:
            self.health_path.parent.mkdir(parents=True, exist_ok=True)
            self.health_path.touch()
            await asyncio.sleep(5)

    async def _follow(self, source: Source) -> None:
        forwarded = 0
        while True:
            if not source.path.exists():
                await asyncio.sleep(1)
                continue
            try:
                current_fingerprint = fingerprint(source.path)
                size = source.path.stat().st_size
                offset = self.checkpoints.get(source.path, current_fingerprint, size)
                with source.path.open("rb") as stream:
                    stream.seek(offset)
                    while True:
                        start = stream.tell()
                        line = stream.readline()
                        if not line:
                            break
                        if not line.endswith(b"\n"):
                            stream.seek(start)
                            break
                        end = stream.tell()
                        try:
                            event = source.parse_line(line.decode("utf-8"))
                        except (UnicodeDecodeError, ValueError, TypeError, KeyError) as exc:
                            logger.warning(
                                "collector_parse_failure source=%s offset=%d error_category=%s",
                                source.name,
                                start,
                                type(exc).__name__,
                            )
                            await self.checkpoints.save(source.path, current_fingerprint, end)
                            continue
                        if event is not None:
                            await self.client.send(event)
                            forwarded += 1
                            if forwarded == 1 or forwarded % 25 == 0:
                                logger.info(
                                    "collector_events_forwarded source=%s count=%d",
                                    source.name,
                                    forwarded,
                                )
                        await self.checkpoints.save(source.path, current_fingerprint, end)
            except OSError as exc:
                logger.warning(
                    "collector_source_read_retry source=%s error_category=%s",
                    source.name,
                    type(exc).__name__,
                )
            await asyncio.sleep(0.5)


async def run() -> None:
    collector = Collector()
    await collector.run()


def main() -> None:
    configure_logging(os.getenv("LOG_LEVEL", "INFO"))
    with suppress(KeyboardInterrupt):
        asyncio.run(run())


if __name__ == "__main__":
    main()
