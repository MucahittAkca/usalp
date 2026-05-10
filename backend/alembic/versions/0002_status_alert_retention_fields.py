"""status, heartbeat and alert dedupe fields

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-10

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("servers", sa.Column("api_key_revoked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("servers", sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True))
    op.alter_column(
        "servers",
        "status",
        existing_type=sa.String(20),
        server_default="offline",
        existing_nullable=False,
    )
    op.execute("UPDATE servers SET status = 'offline' WHERE status = 'active'")

    op.add_column(
        "alerts",
        sa.Column("dedupe_key", sa.String(255), nullable=False, server_default=""),
    )
    op.create_index("ix_alerts_dedupe_key", "alerts", ["dedupe_key"])


def downgrade() -> None:
    op.drop_index("ix_alerts_dedupe_key", "alerts")
    op.drop_column("alerts", "dedupe_key")

    op.alter_column(
        "servers",
        "status",
        existing_type=sa.String(20),
        server_default="active",
        existing_nullable=False,
    )
    op.drop_column("servers", "last_seen")
    op.drop_column("servers", "api_key_revoked_at")
