"""hash stored agent API keys

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-15

"""

from __future__ import annotations

import hashlib

import sqlalchemy as sa

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

API_KEY_HASH_PREFIX = "sha256:"


def _hash_api_key(value: str) -> str:
    return f"{API_KEY_HASH_PREFIX}{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def upgrade() -> None:
    bind = op.get_bind()
    servers = sa.table(
        "servers",
        sa.column("id", sa.Integer()),
        sa.column("api_key", sa.String()),
    )

    rows = bind.execute(sa.select(servers.c.id, servers.c.api_key)).all()
    for server_id, api_key in rows:
        if not api_key or api_key.startswith(API_KEY_HASH_PREFIX):
            continue
        bind.execute(
            servers.update()
            .where(servers.c.id == server_id)
            .values(api_key=_hash_api_key(api_key))
        )


def downgrade() -> None:
    # Hashes cannot be reversed to the original raw API keys.
    pass
