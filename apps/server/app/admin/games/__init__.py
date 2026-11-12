"""The admin pages each game adds, registered by module. To add a game: write
``app/admin/games/<game>.py`` with its views and add them to ``VIEWS`` below. The shared pages
(``app.admin.views``) never change."""

from __future__ import annotations

from sqladmin import ModelView

from app.admin.games import bomb

VIEWS: list[type[ModelView]] = [*bomb.VIEWS]
