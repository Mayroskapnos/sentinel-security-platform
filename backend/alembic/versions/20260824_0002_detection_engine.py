"""Add persistent detection rules, alerts, and alert evidence.

Revision ID: 20260824_0002
Revises: 20260824_0001
Create Date: 2026-08-24 01:00:00+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260824_0002"
down_revision: str | None = "20260824_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "detection_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("rule_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=False),
        sa.Column("rule_type", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=True),
        sa.Column("configuration", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("mitre_tactic", sa.String(length=128), nullable=True),
        sa.Column("mitre_technique_id", sa.String(length=32), nullable=True),
        sa.Column("mitre_technique_name", sa.String(length=255), nullable=True),
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
            "rule_type IN ('threshold', 'sequence', 'single_event')",
            name=op.f("ck_detection_rules_rule_type_values"),
        ),
        sa.CheckConstraint(
            "severity IN ('informational', 'low', 'medium', 'high', 'critical')",
            name=op.f("ck_detection_rules_severity_values"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_detection_rules")),
        sa.UniqueConstraint("rule_id", name=op.f("uq_detection_rules_rule_id")),
    )
    op.create_index(
        "ix_detection_rules_enabled_event_type",
        "detection_rules",
        ["enabled", "event_type"],
    )
    op.create_index("ix_detection_rules_enabled", "detection_rules", ["enabled"])
    op.create_index("ix_detection_rules_event_type", "detection_rules", ["event_type"])
    op.create_index("ix_detection_rules_rule_type", "detection_rules", ["rule_type"])
    op.create_index("ix_detection_rules_severity", "detection_rules", ["severity"])

    op.create_table(
        "alerts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("detection_rule_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=True),
        sa.Column("source_ip", sa.String(length=45), nullable=True),
        sa.Column("destination_ip", sa.String(length=45), nullable=True),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("mitre_tactic", sa.String(length=128), nullable=True),
        sa.Column("mitre_technique_id", sa.String(length=32), nullable=True),
        sa.Column("mitre_technique_name", sa.String(length=255), nullable=True),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("deduplication_key", sa.String(length=512), nullable=False),
        sa.Column("first_event_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_event_at", sa.DateTime(timezone=True), nullable=False),
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
            "risk_score >= 0 AND risk_score <= 100",
            name=op.f("ck_alerts_risk_score_range"),
        ),
        sa.CheckConstraint(
            "severity IN ('informational', 'low', 'medium', 'high', 'critical')",
            name=op.f("ck_alerts_severity_values"),
        ),
        sa.CheckConstraint(
            "status IN ('new', 'investigating', 'resolved', 'false_positive')",
            name=op.f("ck_alerts_status_values"),
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"], ["assets.id"], name=op.f("fk_alerts_asset_id_assets"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["detection_rule_id"],
            ["detection_rules.id"],
            name=op.f("fk_alerts_detection_rule_id_detection_rules"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_alerts")),
    )
    op.create_index(
        "ix_alerts_asset_status_timestamp", "alerts", ["asset_id", "status", "timestamp"]
    )
    op.create_index("ix_alerts_asset_id", "alerts", ["asset_id"])
    op.create_index("ix_alerts_detection_rule_id", "alerts", ["detection_rule_id"])
    op.create_index("ix_alerts_destination_ip", "alerts", ["destination_ip"])
    op.create_index(
        "ix_alerts_rule_deduplication",
        "alerts",
        ["detection_rule_id", "deduplication_key"],
    )
    op.create_index("ix_alerts_severity", "alerts", ["severity"])
    op.create_index("ix_alerts_source_ip", "alerts", ["source_ip"])
    op.create_index("ix_alerts_status", "alerts", ["status"])
    op.create_index("ix_alerts_timestamp", "alerts", ["timestamp"])

    op.create_table(
        "alert_events",
        sa.Column("alert_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["alert_id"],
            ["alerts.id"],
            name=op.f("fk_alert_events_alert_id_alerts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["security_events.id"],
            name=op.f("fk_alert_events_event_id_security_events"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("alert_id", "event_id", name=op.f("pk_alert_events")),
    )


def downgrade() -> None:
    op.drop_table("alert_events")
    op.drop_table("alerts")
    op.drop_table("detection_rules")
