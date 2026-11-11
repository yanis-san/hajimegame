# Wire protocol (v1)

Source of truth: `apps/server/app/realtime/protocol.py`. TypeScript types are generated into
`packages/protocol/src/index.ts` (`make protocol`); a test fails if they are stale.

- Transport: WebSocket at `/ws/{code}`, one JSON object per text frame, max 2048 bytes.
- Every message has a `t` tag and a `v` field (protocol version, currently `1`). Messages with another `v` get
  `error: bad_version`.
- Unknown fields, wrong types and over-long strings are rejected (`error: bad_message`) and counted; more than 20
  invalid messages closes the socket (1008).
- Time values are **milliseconds on the server monotonic clock**. They are only meaningful with the offset the client
  estimates from `ping`/`pong`.

## Connection flow

1. `POST /api/rooms` (headers `Origin` allowed, `X-Hajime-Client: web`) returns `{"code": "K7M2QX"}`.
2. Open `/ws/K7M2QX` (the `Origin` header must be allowed). On unknown code the server sends `error: room_not_found`
   and closes with 4404. If the room lives on another instance the handshake is denied with HTTP 409 and
   `fly-replay: instance=<id>`.
3. Send `join` (or `rejoin`). The server answers `welcome` (player id and **session token, 128 bit**) then `snapshot`.
4. Estimate clock offset with 5 to 8 `ping`s, then keep pinging every 5 s. A connection silent for 45 s is considered a
   zombie and closed.

## Sequence numbers

Broadcast events carry a room-wide `seq` that increases by one per event. A client that sees a gap must `rejoin` to get
a fresh `snapshot`. Private messages (`rejected`, `error`, `welcome`, `pong`) and the ephemeral `typing` relay repeat
the current `seq` without advancing it, so they never create gaps.

## Client to server

| `t` | Fields | Notes |
| --- | --- | --- |
| `join` | `room`, `name` (1-40, cleaned to 20), `avatar` 0-11, `spectator` | Players only in lobby with free seats. Spectators any time. |
| `rejoin` | `room`, `token` | Replaces an older connection of the same player (old one gets `error: replaced`, closes 4000). |
| `ready` | `ready` | Lobby only. |
| `start` | | Host only, needs 2+ connected players, all non-host players ready. Starts the countdown. |
| `settings` | any of `lives` 1-5, `fuse_seconds` 5-20, `max_players` 2-8, `bonus_kana`, `n_penalty` | Host only, lobby only. Partial update. |
| `typing` | `text` (max 32) | Active player only. Relayed to others, max 10 per second, never used for validation. |
| `submit` | `text` (max 32) | Kana, kanji or raw romaji. The server normalizes everything. |
| `ping` | `n`, `t0` | Answered at once, outside the room queue. |
| `kick` | `player_id` | Host only. |
| `add_bot` | `difficulty` (`easy`/`normal`/`hard`) | Host only, lobby. Adds a CPU player; errors: `room_full`, `bots_loading`. |
| `remove_bot` | `player_id` | Host only, lobby. |
| `chat` | `text` (max 200) | Lobby and results. Filtered, 1 message per second. |
| `rematch` | | Host only, after `game_over`. Returns to lobby. |
| `leave` | | Leave immediately without grace period. |

## Server to client

| `t` | Purpose |
| --- | --- |
| `welcome` | Your `player_id`, session `token`, `spectator` flag. |
| `snapshot` | Full state on join and rejoin: phase, host, settings, players, current turn, typing text, last words, results. |
| `patch` | Partial lobby state: `players` (id to full view, or `null` if removed), `host`, `phase`, `settings`, `spectators`, `countdown_ends`. Absent fields are unchanged. |
| `countdown` | `ends_at` (server time). |
| `turn` | `turn`, `player_id`, `fragment`, `deadline`, `fuse_ms`. Animate the fuse from `deadline` minus the clock offset. |
| `typing` | What the active player is typing (ephemeral). |
| `accepted` | Word played: `word`, `reading`, `score_gain`, `score`, `meaning_fr` and `meaning_en` (French may be empty), `example_ja`, `example_en` and `example_fr` (an example sentence
with its translations; all empty for most words, French often empty). |
| `rejected` | Only to the submitter: `reason` is `not_in_dictionary`, `missing_fragment` (classic: fragment absent; shiritori: wrong first kana), `already_used`, `not_your_turn`, `too_late` or `ends_with_n` (shiritori). The turn continues (except `too_late`). |
| `explosion` | Bomb exploded on `player_id`, `lives` left. `cause` is `timeout` or `n_ending` (shiritori penalty). |
| `elimination` | `player_id` is out with final `place`. |
| `life` / `bonus` | Bonus kana progress and extra life. |
| `game_over` | `winner_id` and `results` (place, score, words, longest word). |
| `chat` | Lobby chat line. Plain text, never HTML. |
| `error` | `code` is one of `ErrorCode` in the generated types. |
| `pong` | Echo of `n` and `t0` plus `server_time`. |

## Deadline arbitration

The server stamps each `submit` with its own receive time on the room clock.

- Received at or before `deadline`: judged on its merits (`<=`, so a tie goes to the player).
- Received after `deadline`: `rejected: too_late` and the bomb explodes.
- The bomb timer fires at `deadline`. Both paths go through the single room queue, so there is no race and the outcome
  is deterministic for a given receive order.

## Reconnection

Safari kills WebSockets in the background. The client reconnects with exponential backoff and jitter and sends
`rejoin` with its token. Within the grace period (30 s) the player keeps seat, score and lives, and the game continues
(their turn may time out normally). After the grace period they are eliminated (game) or removed (lobby), and the
host moves to another player if needed. On graceful server shutdown clients receive `error: server_restarting` and
close code 1012: reconnect after a short delay.

## Close codes

| Code | Meaning |
| --- | --- |
| 1008 | Too many invalid messages |
| 1009 | Frame too large |
| 1012 / 1013 | Server restarting / slow consumer |
| 4000 | Replaced by a newer connection |
| 4301 | Wrong instance (reason carries the owner id) |
| 4401 | Bad session token |
| 4403 | Origin not allowed, or kicked |
| 4404 | Room not found |
| 4408 | No join within 15 s |
| 4429 | Rate limited |

## Game mode

The mode (`classic` or `shiritori`) is chosen once, in the body of `POST /api/rooms` (`{"mode": "shiritori"}`), and never changes
afterwards: `settings` has no `mode` field, so a client that sends one gets `error: bad_message`. The mode is visible in
`snapshot.settings.mode`.


Players carry `bot` (true for CPU players, always connected and ready) and `difficulty` (CPU only).
