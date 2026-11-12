"""record finished games: players' guest ids and languages, and the bomb game's turns

Additive only: every new column on an existing table is nullable or has a default, so the previous version of the
server keeps working against this schema (a deployment can be rolled back without undoing the migration).

A game's own data goes in tables named for the game (``bomb_turns``): the common tables stay the same for
every game. This migration was reworked before any deployment existed, so no database has the older shape.

Revision ID: 0002
Revises: 0001
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("games", schema=None) as batch_op:
        batch_op.add_column(sa.Column("mode", sa.String(length=16), nullable=False, server_default="classic"))
        batch_op.add_column(sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("players_count", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("bots_count", sa.Integer(), nullable=False, server_default="0"))

    with op.batch_alter_table("game_players", schema=None) as batch_op:
        batch_op.add_column(sa.Column("guest_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("lang", sa.String(length=2), nullable=True))
        batch_op.add_column(sa.Column("is_bot", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("bot_difficulty", sa.String(length=8), nullable=True))
        batch_op.add_column(sa.Column("explosions", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("avg_response_ms", sa.Integer(), nullable=True))
        batch_op.create_index("ix_game_players_guest_id", ["guest_id"], unique=False)

    op.create_table(
        "bomb_turns",
        sa.Column("game_id", sa.Uuid(), nullable=False),
        sa.Column("turn", sa.Integer(), nullable=False),
        sa.Column("seat", sa.Integer(), nullable=False),
        sa.Column("fragment", sa.String(length=16), nullable=False),
        sa.Column("outcome", sa.String(length=12), nullable=False),
        sa.Column("word", sa.String(length=32), nullable=False),
        sa.Column("reading", sa.String(length=32), nullable=False),
        sa.Column("response_ms", sa.Integer(), nullable=True),
        sa.Column("fuse_ms", sa.Integer(), nullable=False),
        sa.Column("rejected_attempts", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["game_id"], ["games.id"], name=op.f("fk_bomb_turns_game_id_games"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("game_id", "turn", name=op.f("pk_bomb_turns")),
    )
    with op.batch_alter_table("bomb_turns", schema=None) as batch_op:
        batch_op.create_index("ix_bomb_turns_fragment", ["fragment"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("bomb_turns", schema=None) as batch_op:
        batch_op.drop_index("ix_bomb_turns_fragment")
    op.drop_table("bomb_turns")

    with op.batch_alter_table("game_players", schema=None) as batch_op:
        batch_op.drop_index("ix_game_players_guest_id")
        batch_op.drop_column("avg_response_ms")
        batch_op.drop_column("explosions")
        batch_op.drop_column("bot_difficulty")
        batch_op.drop_column("is_bot")
        batch_op.drop_column("lang")
        batch_op.drop_column("guest_id")

    with op.batch_alter_table("games", schema=None) as batch_op:
        batch_op.drop_column("bots_count")
        batch_op.drop_column("players_count")
        batch_op.drop_column("duration_ms")
        batch_op.drop_column("mode")
