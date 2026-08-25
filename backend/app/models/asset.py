from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Float, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.types import JSON_DOCUMENT


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (
        CheckConstraint("risk_score >= 0 AND risk_score <= 100", name="risk_score_range"),
        CheckConstraint(
            "asset_type IN ('workstation', 'server', 'web_server', 'database', "
            "'container', 'network_device', 'unknown')",
            name="asset_type_values",
        ),
        CheckConstraint(
            "status IN ('online', 'offline', 'warning', 'critical', 'unknown')",
            name="asset_status_values",
        ),
        CheckConstraint(
            "criticality IN ('low', 'medium', 'high', 'critical')",
            name="criticality_values",
        ),
        Index("ix_assets_network_zone", "network_zone"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    hostname: Mapped[str] = mapped_column(String(255), unique=True)
    display_name: Mapped[str] = mapped_column(String(255))
    ip_address: Mapped[str] = mapped_column(String(45), unique=True)
    mac_address: Mapped[str | None] = mapped_column(String(17), nullable=True)
    asset_type: Mapped[str] = mapped_column(String(32), index=True)
    operating_system: Mapped[str] = mapped_column(String(255))
    environment: Mapped[str] = mapped_column(String(64))
    network_zone: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), index=True)
    risk_score: Mapped[float] = mapped_column(Float, default=0, index=True)
    criticality: Mapped[str] = mapped_column(String(16), index=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON_DOCUMENT, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    events: Mapped[list["SecurityEvent"]] = relationship(  # noqa: F821
        back_populates="asset", passive_deletes=True
    )
    alerts: Mapped[list["Alert"]] = relationship(  # noqa: F821
        back_populates="asset", passive_deletes=True
    )
