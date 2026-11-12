"""accounts: browsers linked to an account, login sessions, email confirmation date

Additive only (new tables, one nullable column), so the previous server version keeps working against this schema.

Revision ID: 0003
Revises: 0002
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("accounts", schema=None) as batch_op:
        batch_op.add_column(sa.Column("email_verified_at", sa.DateTime(), nullable=True))
    op.create_table(
        "player_guests",
        sa.Column("guest_id", sa.Uuid(), nullable=False),
        sa.Column("player_id", sa.Uuid(), nullable=False),
        sa.Column("linked_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["player_id"], ["players.id"], name=op.f("fk_player_guests_player_id_players"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("guest_id", name=op.f("pk_player_guests")),
    )
    op.create_index(op.f("ix_player_guests_player_id"), "player_guests", ["player_id"])
    op.create_table(
        "login_sessions",
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("player_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["player_id"], ["players.id"], name=op.f("fk_login_sessions_player_id_players"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("token_hash", name=op.f("pk_login_sessions")),
    )
    op.create_index(op.f("ix_login_sessions_player_id"), "login_sessions", ["player_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_login_sessions_player_id"), table_name="login_sessions")
    op.drop_table("login_sessions")
    op.drop_index(op.f("ix_player_guests_player_id"), table_name="player_guests")
    op.drop_table("player_guests")
    with op.batch_alter_table("accounts", schema=None) as batch_op:
        batch_op.drop_column("email_verified_at")
