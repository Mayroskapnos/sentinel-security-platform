from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import text

from app.db.base import Base
from app.models.types import JSON_DOCUMENT


class InvestigationAnalysis(Base):
    __tablename__ = "investigation_analyses"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="status_values",
        ),
        Index("ix_investigation_analyses_incident_created", "incident_id", "created_at"),
        Index("ix_investigation_analyses_status_created", "status", "created_at"),
        Index("ix_investigation_analyses_context_hash", "context_hash"),
        Index(
            "uq_investigation_analyses_one_active",
            "incident_id",
            unique=True,
            postgresql_where=text("status IN ('pending', 'running')"),
            sqlite_where=text("status IN ('pending', 'running')"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    incident_id: Mapped[UUID] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    provider: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(255))
    provider_label: Mapped[str] = mapped_column(String(255))
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    analysis_version: Mapped[str] = mapped_column(String(32), default="1")
    context_hash: Mapped[str] = mapped_column(String(64))
    context_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT)
    executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    observations: Mapped[list[dict[str, Any]]] = mapped_column(JSON_DOCUMENT, default=list)
    correlation_explanation: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, default=dict)
    key_assets: Mapped[list[dict[str, Any]]] = mapped_column(JSON_DOCUMENT, default=list)
    recommended_actions: Mapped[list[dict[str, Any]]] = mapped_column(JSON_DOCUMENT, default=list)
    uncertainties: Mapped[list[dict[str, Any]]] = mapped_column(JSON_DOCUMENT, default=list)
    raw_structured_result: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, default=dict)
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    incident: Mapped["Incident"] = relationship(back_populates="analyses")  # noqa: F821
    messages: Mapped[list["InvestigationMessage"]] = relationship(
        back_populates="analysis", passive_deletes=True
    )


class InvestigationMessage(Base):
    __tablename__ = "investigation_messages"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="role_values"),
        Index("ix_investigation_messages_incident_created", "incident_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    incident_id: Mapped[UUID] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"), index=True
    )
    analysis_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("investigation_analyses.id", ondelete="SET NULL"), nullable=True, index=True
    )
    reply_to_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("investigation_messages.id", ondelete="SET NULL"), nullable=True
    )
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(String(4000))
    evidence_refs: Mapped[list[str]] = mapped_column(JSON_DOCUMENT, default=list)
    context_hash: Mapped[str] = mapped_column(String(64))
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    incident: Mapped["Incident"] = relationship(back_populates="investigation_messages")  # noqa: F821
    analysis: Mapped[InvestigationAnalysis | None] = relationship(back_populates="messages")
