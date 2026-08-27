from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.types import JSON_DOCUMENT


class IncidentAlert(Base):
    __tablename__ = "incident_alerts"
    __table_args__ = (
        CheckConstraint(
            "correlation_score >= 0 AND correlation_score <= 100",
            name="correlation_score_range",
        ),
        UniqueConstraint("alert_id", name="uq_incident_alerts_alert_single_incident"),
        Index("ix_incident_alerts_incident_attached", "incident_id", "attached_at"),
    )

    incident_id: Mapped[UUID] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"), primary_key=True
    )
    alert_id: Mapped[UUID] = mapped_column(
        ForeignKey("alerts.id", ondelete="CASCADE"), primary_key=True
    )
    correlation_score: Mapped[int] = mapped_column(default=0)
    correlation_reasons: Mapped[list[dict[str, Any]]] = mapped_column(JSON_DOCUMENT, default=list)
    attached_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    incident: Mapped["Incident"] = relationship(back_populates="alert_links")
    alert: Mapped["Alert"] = relationship(back_populates="incident_link")  # noqa: F821


class IncidentAsset(Base):
    __tablename__ = "incident_assets"
    __table_args__ = (Index("ix_incident_assets_asset_incident", "asset_id", "incident_id"),)

    incident_id: Mapped[UUID] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"), primary_key=True
    )
    asset_id: Mapped[UUID] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    incident: Mapped["Incident"] = relationship(back_populates="asset_links")
    asset: Mapped["Asset"] = relationship(back_populates="incident_links")  # noqa: F821


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('informational', 'low', 'medium', 'high', 'critical')",
            name="severity_values",
        ),
        CheckConstraint(
            "status IN ('open', 'investigating', 'contained', 'resolved', 'false_positive')",
            name="status_values",
        ),
        CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 100",
            name="confidence_score_range",
        ),
        CheckConstraint("risk_score >= 0 AND risk_score <= 100", name="risk_score_range"),
        Index("ix_incidents_status_last_activity", "status", "last_activity_at"),
        Index("ix_incidents_severity_last_activity", "severity", "last_activity_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    incident_number: Mapped[str] = mapped_column(String(24), unique=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(String(2000))
    severity: Mapped[str] = mapped_column(String(16), index=True)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    confidence_score: Mapped[int] = mapped_column(default=25, index=True)
    risk_score: Mapped[float] = mapped_column(Float, default=0)
    first_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assigned_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary: Mapped[str] = mapped_column(String(2000))
    correlation_reasons: Mapped[list[dict[str, Any]]] = mapped_column(JSON_DOCUMENT, default=list)
    story: Mapped[list[dict[str, Any]]] = mapped_column(JSON_DOCUMENT, default=list)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON_DOCUMENT, default=dict)
    scenario_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("scenario_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    alert_links: Mapped[list[IncidentAlert]] = relationship(
        back_populates="incident", cascade="all, delete-orphan", lazy="raise"
    )
    asset_links: Mapped[list[IncidentAsset]] = relationship(
        back_populates="incident", cascade="all, delete-orphan", lazy="raise"
    )
    scenario_run: Mapped["ScenarioRun | None"] = relationship()  # noqa: F821
    analyses: Mapped[list["InvestigationAnalysis"]] = relationship(  # noqa: F821
        back_populates="incident", passive_deletes=True, lazy="raise"
    )
    investigation_messages: Mapped[list["InvestigationMessage"]] = relationship(  # noqa: F821
        back_populates="incident", passive_deletes=True, lazy="raise"
    )
