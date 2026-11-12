"""The bomb game's pages in the admin: its turns, read-only."""

from __future__ import annotations

from sqladmin import ModelView

from app.db.games.bomb import BombTurn


class BombTurnAdmin(ModelView, model=BombTurn):
    name, name_plural, icon = "Bomb turn", "Bomb turns", "fa-solid fa-bomb"
    column_list = [
        BombTurn.game_id,
        BombTurn.turn,
        BombTurn.fragment,
        BombTurn.outcome,
        BombTurn.word,
        BombTurn.response_ms,
        BombTurn.rejected_attempts,
    ]
    column_searchable_list = [BombTurn.word, BombTurn.fragment]
    page_size = 50
    can_create = can_edit = can_delete = False  # a record of what happened


VIEWS: list[type[ModelView]] = [BombTurnAdmin]
