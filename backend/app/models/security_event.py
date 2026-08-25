from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.types import JSON_DOCUMENT


class SecurityEvent(Base):
    __tablename__ = "security_events"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('informational', 'low', 'medium', 'high', 'critical')",
            name="severity_values",
        ),
        Index("ix_security_events_asset_timestamp", "asset_id", "timestamp"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    source: Mapped[str] = mapped_column(String(64))
    source_ip: Mapped[str | None] = mapped_column(String(45), nullable=True, index=True)
    destination_ip: Mapped[str | None] = mapped_column(String(45), nullable=True, index=True)
    source_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    destination_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    process_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(64), index=True)
    severity: Mapped[str] = mapped_column(String(16), index=True)
    raw_event: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, default=dict)
    normalized_data: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, default=dict)
    asset_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("assets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    asset: Mapped["Asset | None"] = relationship(back_populates="events")  # noqa: F821
    alerts: Mapped[list["Alert"]] = relationship(  # noqa: F821
        secondary="alert_events", back_populates="evidence_events"
    )
