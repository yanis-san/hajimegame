"""The admin's pages for the tables every game shares. A game's own tables are described in
``app/admin/games/<game>.py`` and registered in ``app.admin.games``; nothing here names a game.

What may be done is decided table by table: history (games, who played) is read-only because it is a record
of what happened; accounts can have their email corrected or be removed; sessions can be ended."""

from __future__ import annotations

from sqladmin import ModelView

from app.db.models import Account, Game, GamePlayer, LoginSession, Player


class PlayerAdmin(ModelView, model=Player):
    name, name_plural, icon = "Player", "Players", "fa-solid fa-user"
    column_list = [Player.display_name, Player.is_guest, Player.rank_points, Player.created_at, Player.id]
    column_searchable_list = [Player.display_name]
    column_default_sort = ("created_at", True)
    can_create = False  # players are made by signing up
    form_columns = [Player.display_name]
    page_size = 50


class AccountAdmin(ModelView, model=Account):
    name, name_plural, icon = "Account", "Accounts", "fa-solid fa-key"
    column_list = [
        Account.subject,  # the username, lower-cased
        Account.player,
        Account.provider,
        Account.email,
        Account.email_verified_at,
        Account.created_at,
    ]
    column_searchable_list = [Account.subject, Account.email]
    column_default_sort = ("created_at", True)
    can_create = False  # an account needs a password, which only sign-up can set
    form_columns = [Account.email, Account.email_verified_at]  # the password hash is never shown nor edited
    column_details_exclude_list = [Account.password_hash]
    page_size = 50


class LoginSessionAdmin(ModelView, model=LoginSession):
    name, name_plural, icon = "Sign-in", "Sign-ins", "fa-solid fa-right-to-bracket"
    column_list = [LoginSession.player_id, LoginSession.created_at, LoginSession.expires_at]
    column_details_exclude_list = [LoginSession.token_hash]
    column_default_sort = ("created_at", True)
    can_create = can_edit = False  # deleting one signs that browser out; the token itself is never displayed
    can_export = False


class GameAdmin(ModelView, model=Game):
    name, name_plural, icon = "Game", "Games", "fa-solid fa-gamepad"
    column_list = [
        Game.kind,
        Game.mode,
        Game.ended_at,
        Game.duration_ms,
        Game.players_count,
        Game.bots_count,
        Game.id,
    ]
    column_default_sort = ("ended_at", True)
    column_searchable_list = [Game.kind, Game.mode]
    page_size = 50
    # A record of what happened: never edited. Removing a game (a deletion request, a test game) is
    # allowed and takes its players and turns with it.
    can_create = can_edit = False


class GamePlayerAdmin(ModelView, model=GamePlayer):
    name, name_plural, icon = "Seat", "Seats", "fa-solid fa-chair"
    column_list = [
        GamePlayer.game_id,
        GamePlayer.seat,
        GamePlayer.display_name,
        GamePlayer.place,
        GamePlayer.score,
        GamePlayer.words,
        GamePlayer.is_bot,
        GamePlayer.lang,
    ]
    column_searchable_list = [GamePlayer.display_name]
    page_size = 50
    can_create = can_edit = can_delete = False
    can_export = False  # the rows hold the browsers' guest identifiers
    column_details_exclude_list = [GamePlayer.guest_id]  # it names a browser: stored, never put on a screen


VIEWS: list[type[ModelView]] = [PlayerAdmin, AccountAdmin, LoginSessionAdmin, GameAdmin, GamePlayerAdmin]
