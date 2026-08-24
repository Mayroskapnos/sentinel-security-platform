import math
from datetime import UTC, datetime

from pydantic import BaseModel, Field


def as_utc(value: datetime) -> datetime:
    """Normalize database timestamps, treating timezone-less DB values as UTC."""
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class Page[T](BaseModel):
    items: list[T]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total: int = Field(ge=0)
    pages: int = Field(ge=0)

    @classmethod
    def create(cls, items: list[T], page: int, page_size: int, total: int) -> "Page[T]":
        return cls(
            items=items,
            page=page,
            page_size=page_size,
            total=total,
            pages=math.ceil(total / page_size) if total else 0,
        )
