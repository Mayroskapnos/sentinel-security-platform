"""Add persistent controlled-simulator runs and event attribution.

Revision ID: 20260825_0003
Revises: 20260824_0002
Create Date: 2026-08-25 12:00:00+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260825_0003"
down_revision: str | None = "20260824_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scenario_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("scenario_id", sa.String(length=32), nullable=False),
        sa.Column("scenario_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("active_slot", sa.String(length=32), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_step", sa.Integer(), nullable=False),
        sa.Column("total_steps", sa.Integer(), nullable=False),
        sa.Column("requested_by", sa.String(length=255), nullable=False),
        sa.Column("steps", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("expected_detections", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("targets", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error_message", sa.String(length=2000), nullable=True),
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
            "status IN ('pending', 'running', 'completed', 'failed', 'cancelled')",
            name=op.f("ck_scenario_runs_status_values"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scenario_runs")),
        sa.UniqueConstraint("active_slot", name=op.f("uq_scenario_runs_active_slot")),
    )
    op.create_index("ix_scenario_runs_scenario_id", "scenario_runs", ["scenario_id"])
    op.create_index("ix_scenario_runs_status", "scenario_runs", ["status"])
    op.create_index(
        "ix_scenario_runs_scenario_started", "scenario_runs", ["scenario_id", "started_at"]
    )

    op.add_column("security_events", sa.Column("scenario_run_id", sa.Uuid(), nullable=True))
    op.add_column("security_events", sa.Column("scenario_id", sa.String(length=32), nullable=True))
    op.create_foreign_key(
        op.f("fk_security_events_scenario_run_id_scenario_runs"),
        "security_events",
        "scenario_runs",
        ["scenario_run_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_security_events_scenario_run_id", "security_events", ["scenario_run_id"])
    op.create_index("ix_security_events_scenario_id", "security_events", ["scenario_id"])


def downgrade() -> None:
    op.drop_index("ix_security_events_scenario_id", table_name="security_events")
    op.drop_index("ix_security_events_scenario_run_id", table_name="security_events")
    op.drop_constraint(
        op.f("fk_security_events_scenario_run_id_scenario_runs"),
        "security_events",
        type_="foreignkey",
    )
    op.drop_column("security_events", "scenario_id")
    op.drop_column("security_events", "scenario_run_id")
    op.drop_table("scenario_runs")
