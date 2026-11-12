# Hajime Game - Architecture

Status: milestone A (phases 0 to 4) in progress.

## 1. Goals

A realtime multiplayer BombParty-style game for Japanese words. The server is authoritative; the browser only
renders and sends intents. Guests play with one click, no signup.

## 2. Layout

```text
apps/server   FastAPI: REST + WebSocket, pure game engine, Japanese tooling
apps/web      SvelteKit (Svelte 5 runes), adapter-node, Tailwind + CSS tokens
packages/protocol  JSON Schema + generated TypeScript types
tools/        build_dictionary.py, gen_protocol.py
docs/         this file, PROTOCOL.md, ADR/
```

Server modules (dependencies point downward only):

```text
api/        REST (health, rooms, later accounts)
realtime/   WebSocket handler, Room actor, RoomRegistry (memory + Redis), clock, rate limiting
games/      GameEngine protocol + bomb/ (pure, no I/O, injected clock + RNG)
japanese/   normalization, romaji table, dictionary loader, fragment table
core/       settings, logging, security headers, metrics
db/         SQLAlchemy models + Alembic (accounts, games, scores, seasons, groups, challenges)
```

`games/` and `japanese/` import nothing from FastAPI, Redis or SQLAlchemy. This is enforced by a test.

## 3. Key design decisions

| Topic | Decision |
| --- | --- |
| Authority | Server decides words, turns, deadlines, lives. Client sends `typing`, `submit`, lifecycle intents. |
| Room model | One asyncio task per room draining an event queue (inbound messages, timers). No DB access in a game. |
| Time | Engine takes an injected `Clock` (monotonic ms). Server sends `deadline` in server time; client estimates offset from 5-8 ping/pong (median), animates the fuse with WAAPI. |
| Deadline tie | A word is judged by server receive time (monotonic clock). `received_at <= deadline` accepts; otherwise `too_late`. Timeout event fires at `deadline` and wins ties only if processed first in the single room queue. |
| Protocol | msgspec tagged unions, JSON, `v` + per-room `seq`. TS types generated from the JSON Schema. Snapshot on join/rejoin, `patch`/events afterwards. |
| Reconnect | 128-bit session token per player, grace period (default 30 s), `rejoin` returns exact snapshot. New connection replaces old one. |
| Registry | `RoomRegistry` interface. `MemoryRegistry` for v1, `RedisRegistry` maps room code to owning instance id (SET NX + TTL heartbeat); non-owner instances answer "redirect". Tested with two instances. |
| Dictionary | JMdict compiled by `tools/build_dictionary.py` into a versioned gzip JSON (committed). Loaded into immutable dicts at startup. |
| Difficulty | No word levels: every dictionary word is playable. Difficulty is only the fuse time and the lives; the fragment tier follows how fast a player answers. See `docs/DICTIONARY.md`. |
| Fragments | Units are a kana plus following small kana. 1-3 unit n-grams with at least N (default 80) valid words. Plain substring test that never cuts a unit. |
| Data schema | Alembic migration 0001 creates players, games, game_players, seasons, groups, challenges up front; 0002 adds the per-turn record (`turns`) and each player's guest id and language. Finished games are written after `game_over` by a background recorder (`app/db/recorder.py`), never during a game; without `HAJIME_DATABASE_URL` nothing is stored. See ADR 0007. Each game owns its tables (`bomb_turns`) and its statistics; see `docs/ADDING_A_GAME.md`. |

## 4. Ambiguities and defaults chosen

| Ambiguity | Default |
| --- | --- |
| Spectators | Join when the room is full or the game is running; read-only; do not count toward 8 players. |
| Lobby chat | Plain text, 200 chars max, rate limited, profanity filtered, rendered as text only. |
| Avatar | A set of mascot colours/shapes (SVG), chosen client side, sent as an id (0-11). |
| Nickname filter | Small FR/EN/JA blocklist after NFKC + casefold + leetspeak fold. |
| Timeout vs tie | See table above. |
| Redis absent | Rate limiting and registry fall back to in-memory. |
| Fonts | Fontsource, self-hosted, latin + Japanese subsets where available. |
| Sounds | Synthesised with WebAudio (no binary assets, no licensing risk). |
| Bonus kana (45 kana life) | Engine supports it behind a setting; UI exposure is milestone C. |
| Tension ramp | Engine setting `tension`; fuse shrinks per round to a floor, harder fragment tier unlocks. |

## 5. Test strategy

Pure units with hypothesis (normalization, romaji), deterministic engine scenarios, 10 000 simulated games with
invariants, real WebSocket integration tests against an in-process ASGI server, a load script (locust), vitest for
the web client, Playwright for end to end. Coverage gates: 95% engine and Japanese, 85% server, 80% web logic.

## 6. Milestone A phases

0 foundations, 1 Japanese, 2 engine, 3 realtime, 4 interface. Each ends green, committed and documented.
