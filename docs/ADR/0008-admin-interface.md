# 0008 An admin interface for the operator (SQLAdmin)

Status: accepted. The person who runs the site can browse and correct what is stored without writing SQL.

- **What.** [SQLAdmin](https://github.com/aminalaee/sqladmin) (the closest thing to Django's admin for SQLAlchemy and
  FastAPI), mounted on the game server at `/admin`. It reads the same models as the game, so a new column shows up
  without extra code. Code: `app/admin/`.
- **Closed by default.** It does not exist unless `HAJIME_ADMIN_PASSWORD_HASH` is set (an empty value counts as unset).
  A half configuration (no database, a short secret, a hash that is not Argon2) stops the server from starting rather
  than leaving a door open. Make the values with `uv run python -m app.admin.passwd`.
- **One operator, own login.** Separate from players' accounts: the password only exists on the server as an Argon2
  hash. Five wrong attempts per address per 15 minutes and 30 per hour overall (a wrong name takes as long as a wrong
  password and gets the same answer). The session is a signed cookie, SameSite=Strict, Secure in production, 8 hours.
- **Read-only where it is a record.** Games, seats and bomb turns cannot be edited; a game can be deleted (a deletion
  request, a test game) and takes its seats and turns with it. Players and accounts can be corrected (name, email), not
  created, because an account needs a password that only sign-up sets. Sign-ins can be ended. Password hashes, session
  tokens and guest identifiers are never displayed and are not exported.
- **Audit.** Every create, change and delete is logged (`admin_action`: who, table, row, what changed).
- **Optional network limit.** `ADMIN_ALLOWED_IPS` in the server's `.env` makes Caddy answer 404 to every other address.
- **Its own page policy.** The admin's pages need their own scripts and styles, so `/admin` gets a Content-Security-Policy
  that allows them (same origin only, no framing); every other response keeps `default-src 'none'`.
- **One game, one set of pages.** Shared tables are described in `app/admin/views.py`; a game's own tables in
  `app/admin/games/<game>.py`, registered in `app/admin/games/__init__.py`. An architecture test keeps the shared part
  free of any particular game (docs/ADDING_A_GAME.md).
- **Not built.** Roles (a second, read-only operator), two-factor sign-in, and an in-admin audit table. Today: one
  operator, the log, and the optional address limit.
