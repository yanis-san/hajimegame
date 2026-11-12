# 0007 Game data in PostgreSQL, guest identity now, accounts next

Status: accepted. Finished games are stored in PostgreSQL from the first deployment; accounts come later, and are
designed for now so that nobody's history is lost when they arrive.

- **Why now.** Statistics (how long games last, which prompts are too hard, who comes back, which language is used)
  cannot be recovered afterwards, and a player's history cannot be linked to an account later unless the games were
  stored with something that identifies the browser from the start.
- **Never during a game.** A room hands the finished game to a recorder that only queues it; one background task
  writes it, with retries, and drops the oldest records if the database stays down (counted in
  `hajime_game_records_total`). The database being down never slows or stops a game. Without `HAJIME_DATABASE_URL`
  nothing is stored (development and tests).
- **Guest identity.** The browser makes a random UUID once, keeps it in localStorage and sends it when joining. It is
  stored in `game_players.guest_id` and never sent to other players. It names a browser, not a person.
- **Accounts (next).** Guest or account: playing as a guest stays the default and stays complete. Signing up (Google or
  email) creates a `players` and an `accounts` row, then one statement links the browser's past games:
  `update game_players set player_id = :player where guest_id = :guest and player_id is null`. Ranks, leaderboards
  and friends build on `player_id`. Open decisions for that step: the sign-in methods and an email provider for
  verification and password reset, session handling (an httpOnly cookie), and account deletion.
- **Only what is needed.** No IP address, no device information, no tracking cookie. What is stored is described to
  players on the credits page.
- **Operations.** Migrations only add, are applied by `deploy.sh` before the new version starts, and a failure stops the
  deployment untouched. Daily dumps, 14 days, with a tested restore (docs/DEPLOY.md).
