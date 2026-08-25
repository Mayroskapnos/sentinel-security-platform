from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.types import JSON_DOCUMENT


class ScenarioRun(Base):
    __tablename__ = "scenario_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', 'cancelled')",
            name="status_values",
        ),
        Index("ix_scenario_runs_scenario_started", "scenario_id", "started_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    scenario_id: Mapped[str] = mapped_column(String(32), index=True)
    scenario_name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), index=True)
    # A nullable unique slot is a database-backed guarantee that only one run is active.
    active_slot: Mapped[str | None] = mapped_column(String(32), nullable=True, unique=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_step: Mapped[int] = mapped_column(Integer, default=0)
    total_steps: Mapped[int] = mapped_column(Integer)
    requested_by: Mapped[str] = mapped_column(String(255), default="local-user")
    steps: Mapped[list[dict[str, Any]]] = mapped_column(JSON_DOCUMENT, default=list)
    expected_detections: Mapped[list[str]] = mapped_column(JSON_DOCUMENT, default=list)
    targets: Mapped[list[str]] = mapped_column(JSON_DOCUMENT, default=list)
    result: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, default=dict)
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    events: Mapped[list["SecurityEvent"]] = relationship(  # noqa: F821
        back_populates="scenario_run", passive_deletes=True
    )
