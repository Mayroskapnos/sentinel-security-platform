"""Add persistent incident correlation relationships.

Revision ID: 20260826_0005
Revises: 20260825_0004
Create Date: 2026-08-26 10:00:00+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260826_0005"
down_revision: str | None = "20260825_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "incidents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("incident_number", sa.String(length=24), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("confidence_score", sa.Integer(), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("first_activity_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assigned_to", sa.String(length=255), nullable=True),
        sa.Column("summary", sa.String(length=2000), nullable=False),
        sa.Column(
            "correlation_reasons",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("story", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("scenario_run_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 100",
            name=op.f("ck_incidents_confidence_score_range"),
        ),
        sa.CheckConstraint(
            "risk_score >= 0 AND risk_score <= 100",
            name=op.f("ck_incidents_risk_score_range"),
        ),
        sa.CheckConstraint(
            "severity IN ('informational', 'low', 'medium', 'high', 'critical')",
            name=op.f("ck_incidents_severity_values"),
        ),
        sa.CheckConstraint(
            "status IN ('open', 'investigating', 'contained', 'resolved', 'false_positive')",
            name=op.f("ck_incidents_status_values"),
        ),
        sa.ForeignKeyConstraint(
            ["scenario_run_id"],
            ["scenario_runs.id"],
            name=op.f("fk_incidents_scenario_run_id_scenario_runs"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_incidents")),
        sa.UniqueConstraint("incident_number", name=op.f("uq_incidents_incident_number")),
    )
    op.create_index("ix_incidents_severity", "incidents", ["severity"])
    op.create_index("ix_incidents_status", "incidents", ["status"])
    op.create_index("ix_incidents_confidence_score", "incidents", ["confidence_score"])
    op.create_index("ix_incidents_first_activity_at", "incidents", ["first_activity_at"])
    op.create_index("ix_incidents_last_activity_at", "incidents", ["last_activity_at"])
    op.create_index("ix_incidents_scenario_run_id", "incidents", ["scenario_run_id"])
    op.create_index(
        "ix_incidents_status_last_activity", "incidents", ["status", "last_activity_at"]
    )
    op.create_index(
        "ix_incidents_severity_last_activity", "incidents", ["severity", "last_activity_at"]
    )

    op.create_table(
        "incident_alerts",
        sa.Column("incident_id", sa.Uuid(), nullable=False),
        sa.Column("alert_id", sa.Uuid(), nullable=False),
        sa.Column("correlation_score", sa.Integer(), nullable=False),
        sa.Column(
            "correlation_reasons",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "attached_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "correlation_score >= 0 AND correlation_score <= 100",
            name=op.f("ck_incident_alerts_correlation_score_range"),
        ),
        sa.ForeignKeyConstraint(
            ["alert_id"],
            ["alerts.id"],
            name=op.f("fk_incident_alerts_alert_id_alerts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["incident_id"],
            ["incidents.id"],
            name=op.f("fk_incident_alerts_incident_id_incidents"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("incident_id", "alert_id", name=op.f("pk_incident_alerts")),
        sa.UniqueConstraint("alert_id", name=op.f("uq_incident_alerts_alert_single_incident")),
    )
    op.create_index(
        "ix_incident_alerts_incident_attached",
        "incident_alerts",
        ["incident_id", "attached_at"],
    )

    op.create_table(
        "incident_assets",
        sa.Column("incident_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["assets.id"],
            name=op.f("fk_incident_assets_asset_id_assets"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["incident_id"],
            ["incidents.id"],
            name=op.f("fk_incident_assets_incident_id_incidents"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("incident_id", "asset_id", name=op.f("pk_incident_assets")),
    )
    op.create_index(
        "ix_incident_assets_asset_incident",
        "incident_assets",
        ["asset_id", "incident_id"],
    )


def downgrade() -> None:
    op.drop_table("incident_assets")
    op.drop_table("incident_alerts")
    op.drop_table("incidents")
