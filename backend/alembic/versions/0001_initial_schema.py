"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-02

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # servers
    op.create_table(
        "servers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("hostname", sa.String(255), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=False),
        sa.Column("api_key", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_servers_api_key", "servers", ["api_key"], unique=True)

    # metrics
    op.create_table(
        "metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("server_id", sa.Integer(), sa.ForeignKey("servers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cpu_percent", sa.Float(), nullable=False),
        sa.Column("ram_percent", sa.Float(), nullable=False),
        sa.Column("disk_percent", sa.Float(), nullable=False),
        sa.Column("network_in_bytes", sa.BigInteger(), nullable=False),
        sa.Column("network_out_bytes", sa.BigInteger(), nullable=False),
        sa.Column("load_avg_1", sa.Float(), nullable=False),
        sa.Column("load_avg_5", sa.Float(), nullable=False),
        sa.Column("load_avg_15", sa.Float(), nullable=False),
        sa.Column("raw_json", sa.JSON(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_metrics_recorded_at", "metrics", ["recorded_at"])
    op.create_index("ix_metrics_server_recorded", "metrics", ["server_id", "recorded_at"])

    # service_statuses
    op.create_table(
        "service_statuses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("server_id", sa.Integer(), sa.ForeignKey("servers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("service_name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("checked_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # log_entries
    op.create_table(
        "log_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("server_id", sa.Integer(), sa.ForeignKey("servers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_file", sa.String(512), nullable=False),
        sa.Column("level", sa.String(20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False, server_default=""),
        sa.Column("raw_line", sa.Text(), nullable=False),
        sa.Column("logged_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_log_entries_level", "log_entries", ["level"])
    op.create_index("ix_logs_server_logged", "log_entries", ["server_id", "logged_at"])

    # alerts
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("server_id", sa.Integer(), sa.ForeignKey("servers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # ai_analyses
    op.create_table(
        "ai_analyses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("alert_id", sa.Integer(), sa.ForeignKey("alerts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("server_id", sa.Integer(), sa.ForeignKey("servers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("causes", sa.Text(), nullable=False),
        sa.Column("commands", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("ai_analyses")
    op.drop_table("alerts")
    op.drop_table("log_entries")
    op.drop_table("service_statuses")
    op.drop_table("metrics")
    op.drop_index("ix_servers_api_key", "servers")
    op.drop_table("servers")
