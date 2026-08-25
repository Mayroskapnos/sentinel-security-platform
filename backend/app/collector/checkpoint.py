import asyncio
import json
import os
from pathlib import Path
from typing import TypedDict


class Cursor(TypedDict):
    fingerprint: str
    offset: int


class CheckpointStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = asyncio.Lock()
        self._values: dict[str, Cursor] = self._load()

    def get(self, source: Path, fingerprint: str, size: int) -> int:
        cursor = self._values.get(str(source))
        if cursor is None or cursor["fingerprint"] != fingerprint or cursor["offset"] > size:
            return 0
        return cursor["offset"]

    async def save(self, source: Path, fingerprint: str, offset: int) -> None:
        async with self._lock:
            self._values[str(source)] = {"fingerprint": fingerprint, "offset": offset}
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(
                json.dumps(self._values, indent=2, sort_keys=True), encoding="utf-8"
            )
            os.replace(temporary, self.path)

    def _load(self) -> dict[str, Cursor]:
        try:
            document = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return {}
        if not isinstance(document, dict):
            return {}
        result: dict[str, Cursor] = {}
        for key, value in document.items():
            if (
                isinstance(key, str)
                and isinstance(value, dict)
                and isinstance(value.get("fingerprint"), str)
                and isinstance(value.get("offset"), int)
            ):
                result[key] = {
                    "fingerprint": value["fingerprint"],
                    "offset": value["offset"],
                }
        return result


def fingerprint(path: Path) -> str:
    metadata = path.stat()
    return f"{metadata.st_dev}:{metadata.st_ino}"
