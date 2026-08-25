import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from app.collector.adapters import (
    DatabaseClientConnectionAdapter,
    LinuxAuthAdapter,
    NetworkConnectionAdapter,
    PostgresAdapter,
    ProcessAdapter,
    ServiceHealthAdapter,
    SudoAdapter,
    WebAccessAdapter,
    WebAuthenticationAdapter,
)
from app.schemas.security_event import SecurityEventCreate


class Adapter(Protocol):
    def parse(self, record: Mapping[str, Any]) -> SecurityEventCreate | None: ...


@dataclass(frozen=True)
class Source:
    name: str
    path: Path
    adapters: Mapping[str, Adapter]

    def parse_line(self, line: str) -> SecurityEventCreate | None:
        document = json.loads(line)
        if not isinstance(document, dict):
            raise ValueError("source line must contain one JSON object")
        if self.name == "postgresql":
            return self.adapters["postgresql"].parse(document)
        kind = document.get("kind")
        if not isinstance(kind, str) or kind not in self.adapters:
            raise ValueError(f"unsupported {self.name} record kind: {kind!r}")
        return self.adapters[kind].parse(document)


def sources(log_root: Path) -> list[Source]:
    web_adapters: dict[str, Adapter] = {
        WebAccessAdapter.kind: WebAccessAdapter(),
        WebAuthenticationAdapter.kind: WebAuthenticationAdapter(),
        ServiceHealthAdapter.kind: ServiceHealthAdapter(),
    }
    host_adapters: dict[str, Adapter] = {
        DatabaseClientConnectionAdapter.kind: DatabaseClientConnectionAdapter(),
        LinuxAuthAdapter.kind: LinuxAuthAdapter(),
        NetworkConnectionAdapter.kind: NetworkConnectionAdapter(),
        ProcessAdapter.kind: ProcessAdapter(),
        ServiceHealthAdapter.kind: ServiceHealthAdapter(),
        SudoAdapter.kind: SudoAdapter(),
    }
    return [
        Source("web", log_root / "web" / "events.jsonl", web_adapters),
        Source("employee-01", log_root / "employee-01" / "events.jsonl", host_adapters),
        Source("employee-02", log_root / "employee-02" / "events.jsonl", host_adapters),
        Source("admin", log_root / "admin" / "events.jsonl", host_adapters),
        Source(
            "postgresql",
            log_root / "database" / "postgresql.json",
            {
                "postgresql": PostgresAdapter(
                    {
                        "10.10.30.30": "10.10.10.10",
                    }
                )
            },
        ),
    ]
