# Adding a game

The site is built so that each game is isolated: its rules, what it records, its tables, its statistics and its
screens live in the game's own folders, and nothing in another game or in the shared parts has to change. The bomb
game (`bomb`) is the reference: copy its shape.

## What is shared, and what belongs to a game

| Shared by every game | Belongs to one game |
| --- | --- |
| `app/games/base.py` (engine protocol), `app/games/recording.py` (the record of a finished game) | `app/games/<game>/`: engine, events, settings, `recording.py` |
| `app/db/models.py`: `games` and `game_players` (who played, place, score, guest id, language) | `app/db/games/<game>.py`: the game's own tables, its `GameStore`, its statistics queries |
| `app/api/me.py`: `GET /api/me/stats/{game}` (identity, rate limit, checks) | `app/api/games/<game>.py`: the game's statistics provider and view |
| `app/db/recorder.py`: writes any finished game in the background | `app/realtime/protocol.py`: the game's wire structs, prefixed with its name (`Bomb...`) |
| `src/lib/design/`: buttons, modals, cards | `src/lib/games/<game>/`: its screens and its statistics dashboard |

`tests/test_architecture.py` fails if one game imports another, if the shared database model mentions a particular
game, or if a pure game package imports FastAPI, a database or the network.

## Server, in order

1. **The rules.** `app/games/<game>/`: a pure engine (no network, no database, no system clock: both are injected)
   that implements `GameEngine`, and its events.
2. **What it records.** `app/games/<game>/recording.py`: a class with `on_event(event, now)` and `finish(results,
   ended_at, now)` that returns a `GameRecord` (`kind="<game>"`, the common fields, and `detail=` a frozen dataclass of
   the game's own data). Test it without any database.
3. **Its tables.** `app/db/games/<game>.py`: ORM tables named `<game>_...` (declared on `Base`, with a foreign key to
   `games.id` and `ondelete="CASCADE"`), a `GameStore` whose `detail_rows(record)` returns them, and `STORE = ...`.
   Register it in `STORES` (`app/db/games/__init__.py`). Add an Alembic migration that creates the tables: migrations
   only add (new tables, new nullable or defaulted columns), because a rollback must still work.
4. **Its statistics.** The queries in the same module; a provider in `app/api/games/<game>.py` (a `modes` property and
   an async `view(...)` returning a msgspec struct); register it in `PROVIDERS` (`app/api/games/__init__.py`). The route,
   the identity check and the rate limit are already there.
5. **Its wire types.** Structs in `app/realtime/protocol.py` named for the game, added to `views` in
   `tools/gen_protocol.py`, then `pnpm protocol`.
6. **The room.** Today `Room` creates the bomb engine and its recording directly; a second game is the moment to make
   that choice depend on the game (a small factory returning the engine and the recording). Everything it hands to the
   recorder is already game-neutral.

## Web, in order

1. `src/lib/games/<game>/`: its screens and its `<Game>Stats.svelte` dashboard.
2. `src/lib/games/registry.ts`: add the id to `GAME_IDS` and its view type to `StatsByGame`; `src/lib/games/stats.ts`:
   add the dashboard and the game's name. The statistics route (`/stats/<game>`), the picker and the API client pick it
   up from there.
3. Messages for every language in `src/lib/i18n/`, tests, and an e2e test of the game's screens.

## Data and privacy

A game records only what it needs, and never an address or a device identifier. If the game stores anything beyond
nicknames, scores and the game's own moves, say so on the credits page and in `docs/DEPLOY.md`.
