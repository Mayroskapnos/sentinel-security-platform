from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.types import JSON_DOCUMENT


class AlertEvent(Base):
    __tablename__ = "alert_events"

    alert_id: Mapped[UUID] = mapped_column(
        ForeignKey("alerts.id", ondelete="CASCADE"), primary_key=True
    )
    event_id: Mapped[UUID] = mapped_column(
        ForeignKey("security_events.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('informational', 'low', 'medium', 'high', 'critical')",
            name="severity_values",
        ),
        CheckConstraint(
            "status IN ('new', 'investigating', 'resolved', 'false_positive')",
            name="status_values",
        ),
        CheckConstraint("risk_score >= 0 AND risk_score <= 100", name="risk_score_range"),
        Index("ix_alerts_rule_deduplication", "detection_rule_id", "deduplication_key"),
        Index("ix_alerts_asset_status_timestamp", "asset_id", "status", "timestamp"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(String(2000))
    severity: Mapped[str] = mapped_column(String(16), index=True)
    status: Mapped[str] = mapped_column(String(32), default="new", index=True)
    detection_rule_id: Mapped[UUID] = mapped_column(
        ForeignKey("detection_rules.id", ondelete="RESTRICT"), index=True
    )
    asset_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("assets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_ip: Mapped[str | None] = mapped_column(String(45), nullable=True, index=True)
    destination_ip: Mapped[str | None] = mapped_column(String(45), nullable=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    risk_score: Mapped[float] = mapped_column(Float, default=0)
    mitre_tactic: Mapped[str | None] = mapped_column(String(128), nullable=True)
    mitre_technique_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    mitre_technique_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON_DOCUMENT, default=dict)
    deduplication_key: Mapped[str] = mapped_column(String(512))
    first_event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    detection_rule: Mapped["DetectionRule"] = relationship(back_populates="alerts")  # noqa: F821
    asset: Mapped["Asset | None"] = relationship(back_populates="alerts")  # noqa: F821
    evidence_events: Mapped[list["SecurityEvent"]] = relationship(  # noqa: F821
        secondary="alert_events", back_populates="alerts", lazy="raise"
    )

    @property
    def evidence_count(self) -> int:
        return int(self.evidence.get("event_count", 0))
