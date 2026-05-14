"""server group, tags and environment fields

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-10

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "servers",
        sa.Column("environment", sa.String(50), nullable=False, server_default="production"),
    )
    op.add_column(
        "servers",
        sa.Column("group_name", sa.String(100), nullable=False, server_default=""),
    )
    op.add_column("servers", sa.Column("tags", sa.JSON(), nullable=True))
    op.execute("UPDATE servers SET tags = '[]' WHERE tags IS NULL")
    op.alter_column("servers", "tags", existing_type=sa.JSON(), nullable=False)
    op.create_index("ix_servers_environment", "servers", ["environment"])
    op.create_index("ix_servers_group_name", "servers", ["group_name"])


def downgrade() -> None:
    op.drop_index("ix_servers_group_name", "servers")
    op.drop_index("ix_servers_environment", "servers")
    op.drop_column("servers", "tags")
    op.drop_column("servers", "group_name")
    op.drop_column("servers", "environment")
