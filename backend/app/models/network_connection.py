from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.types import JSON_DOCUMENT


class NetworkConnection(Base):
    """One durable, aggregated relationship between two known assets."""

    __tablename__ = "network_connections"
    __table_args__ = (
        CheckConstraint("connection_count >= 1", name="connection_count_positive"),
        Index("ix_network_connections_source_last_seen", "source_asset_id", "last_seen"),
        Index(
            "ix_network_connections_destination_last_seen",
            "destination_asset_id",
            "last_seen",
        ),
        Index("ix_network_connections_last_seen", "last_seen"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    relationship_key: Mapped[str] = mapped_column(String(64), unique=True)
    source_asset_id: Mapped[UUID] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), index=True
    )
    destination_asset_id: Mapped[UUID] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), index=True
    )
    source_ip: Mapped[str] = mapped_column(String(45))
    destination_ip: Mapped[str] = mapped_column(String(45))
    source_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    destination_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    protocol: Mapped[str] = mapped_column(String(32), default="unknown")
    connection_type: Mapped[str] = mapped_column(String(64))
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    connection_count: Mapped[int] = mapped_column(Integer, default=1)
    last_status: Mapped[str] = mapped_column(String(64))
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON_DOCUMENT, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    source_asset: Mapped["Asset"] = relationship(foreign_keys=[source_asset_id])  # noqa: F821
    destination_asset: Mapped["Asset"] = relationship(  # noqa: F821
        foreign_keys=[destination_asset_id]
    )
