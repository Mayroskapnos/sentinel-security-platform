from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.types import JSON_DOCUMENT


class DetectionRule(Base):
    __tablename__ = "detection_rules"
    __table_args__ = (
        CheckConstraint(
            "rule_type IN ('threshold', 'sequence', 'single_event')",
            name="rule_type_values",
        ),
        CheckConstraint(
            "severity IN ('informational', 'low', 'medium', 'high', 'critical')",
            name="severity_values",
        ),
        Index("ix_detection_rules_enabled_event_type", "enabled", "event_type"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    rule_id: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(String(2000))
    rule_type: Mapped[str] = mapped_column(String(32), index=True)
    severity: Mapped[str] = mapped_column(String(16), index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    event_type: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, default=dict)
    mitre_tactic: Mapped[str | None] = mapped_column(String(128), nullable=True)
    mitre_technique_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    mitre_technique_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    alerts: Mapped[list["Alert"]] = relationship(  # noqa: F821
        back_populates="detection_rule", passive_deletes=True
    )
