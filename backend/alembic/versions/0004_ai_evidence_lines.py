"""AI analysis evidence lines

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-10

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ai_analyses",
        sa.Column("evidence_lines", sa.Text(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("ai_analyses", "evidence_lines")
