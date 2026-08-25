from secrets import compare_digest
from typing import Annotated

from fastapi import Header, status

from app.core.config import get_settings
from app.core.errors import AppError


def verify_collector_key(
    provided_key: Annotated[str | None, Header(alias="X-Sentinel-Collector-Key")] = None,
) -> None:
    configured_key = get_settings().collector_api_key
    if configured_key is None:
        return
    if provided_key is None or not compare_digest(provided_key, configured_key):
        raise AppError(
            code="COLLECTOR_AUTHENTICATION_FAILED",
            message="A valid collector key is required for event ingestion.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
