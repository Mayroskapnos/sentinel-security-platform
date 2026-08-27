"""Add optional Incident investigation analyses and bounded Q&A history.

Revision ID: 20260826_0006
Revises: 20260826_0005
Create Date: 2026-08-26 14:00:00+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260826_0006"
down_revision: str | None = "20260826_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "investigation_analyses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("incident_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("provider_label", sa.String(length=255), nullable=False),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("analysis_version", sa.String(length=32), nullable=False),
        sa.Column("context_hash", sa.String(length=64), nullable=False),
        sa.Column("context_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("executive_summary", sa.Text(), nullable=True),
        sa.Column("observations", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "correlation_explanation",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("key_assets", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("recommended_actions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("uncertainties", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("raw_structured_result", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error_message", sa.String(length=2000), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
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
            "status IN ('pending', 'running', 'completed', 'failed')",
            name=op.f("ck_investigation_analyses_status_values"),
        ),
        sa.ForeignKeyConstraint(
            ["incident_id"],
            ["incidents.id"],
            name=op.f("fk_investigation_analyses_incident_id_incidents"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_investigation_analyses")),
    )
    op.create_index(
        "ix_investigation_analyses_incident_id",
        "investigation_analyses",
        ["incident_id"],
    )
    op.create_index("ix_investigation_analyses_status", "investigation_analyses", ["status"])
    op.create_index(
        "ix_investigation_analyses_incident_created",
        "investigation_analyses",
        ["incident_id", "created_at"],
    )
    op.create_index(
        "ix_investigation_analyses_status_created",
        "investigation_analyses",
        ["status", "created_at"],
    )
    op.create_index(
        "ix_investigation_analyses_context_hash",
        "investigation_analyses",
        ["context_hash"],
    )
    op.create_index(
        "uq_investigation_analyses_one_active",
        "investigation_analyses",
        ["incident_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('pending', 'running')"),
    )

    op.create_table(
        "investigation_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("incident_id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=True),
        sa.Column("reply_to_id", sa.Uuid(), nullable=True),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.String(length=4000), nullable=False),
        sa.Column("evidence_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("context_hash", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("model", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('user', 'assistant')",
            name=op.f("ck_investigation_messages_role_values"),
        ),
        sa.ForeignKeyConstraint(
            ["analysis_id"],
            ["investigation_analyses.id"],
            name=op.f("fk_investigation_messages_analysis_id_investigation_analyses"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["incident_id"],
            ["incidents.id"],
            name=op.f("fk_investigation_messages_incident_id_incidents"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["reply_to_id"],
            ["investigation_messages.id"],
            name=op.f("fk_investigation_messages_reply_to_id_investigation_messages"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_investigation_messages")),
    )
    op.create_index(
        "ix_investigation_messages_incident_id",
        "investigation_messages",
        ["incident_id"],
    )
    op.create_index(
        "ix_investigation_messages_analysis_id",
        "investigation_messages",
        ["analysis_id"],
    )
    op.create_index(
        "ix_investigation_messages_incident_created",
        "investigation_messages",
        ["incident_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("investigation_messages")
    op.drop_table("investigation_analyses")
