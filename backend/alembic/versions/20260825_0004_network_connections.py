"""Add persistent aggregated network relationships.

Revision ID: 20260825_0004
Revises: 20260825_0003
Create Date: 2026-08-25 15:00:00+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260825_0004"
down_revision: str | None = "20260825_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "network_connections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("relationship_key", sa.String(length=64), nullable=False),
        sa.Column("source_asset_id", sa.Uuid(), nullable=False),
        sa.Column("destination_asset_id", sa.Uuid(), nullable=False),
        sa.Column("source_ip", sa.String(length=45), nullable=False),
        sa.Column("destination_ip", sa.String(length=45), nullable=False),
        sa.Column("source_port", sa.Integer(), nullable=True),
        sa.Column("destination_port", sa.Integer(), nullable=True),
        sa.Column("protocol", sa.String(length=32), nullable=False),
        sa.Column("connection_type", sa.String(length=64), nullable=False),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("connection_count", sa.Integer(), nullable=False),
        sa.Column("last_status", sa.String(length=64), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
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
            "connection_count >= 1",
            name=op.f("ck_network_connections_connection_count_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["destination_asset_id"],
            ["assets.id"],
            name=op.f("fk_network_connections_destination_asset_id_assets"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_asset_id"],
            ["assets.id"],
            name=op.f("fk_network_connections_source_asset_id_assets"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_network_connections")),
        sa.UniqueConstraint(
            "relationship_key", name=op.f("uq_network_connections_relationship_key")
        ),
    )
    op.create_index(
        "ix_network_connections_source_asset_id",
        "network_connections",
        ["source_asset_id"],
    )
    op.create_index(
        "ix_network_connections_destination_asset_id",
        "network_connections",
        ["destination_asset_id"],
    )
    op.create_index(
        "ix_network_connections_source_last_seen",
        "network_connections",
        ["source_asset_id", "last_seen"],
    )
    op.create_index(
        "ix_network_connections_destination_last_seen",
        "network_connections",
        ["destination_asset_id", "last_seen"],
    )
    op.create_index("ix_network_connections_last_seen", "network_connections", ["last_seen"])


def downgrade() -> None:
    op.drop_table("network_connections")
