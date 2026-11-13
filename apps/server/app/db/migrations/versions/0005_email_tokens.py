"""email_tokens: one-time links that confirm an e-mail address

Additive only (a new table), so the previous server version keeps working against this schema.

Revision ID: 0005
Revises: 0004
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "email_tokens",
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("player_id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["player_id"], ["players.id"], name=op.f("fk_email_tokens_player_id_players"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("token_hash", name=op.f("pk_email_tokens")),
    )
    op.create_index(op.f("ix_email_tokens_player_id"), "email_tokens", ["player_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_email_tokens_player_id"), table_name="email_tokens")
    op.drop_table("email_tokens")
