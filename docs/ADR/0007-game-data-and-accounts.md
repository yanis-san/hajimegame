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
- **One game, one set of tables.** Every game stores the same common rows (`games`, `game_players`); what only
  one game has lives in tables named for it (`bomb_turns`), written by that game's own store, read by that game's
  statistics, and shown by that game's dashboard. Adding a game touches none of the others, and an architecture
  test enforces it (docs/ADDING_A_GAME.md). The detail rows are written after the common ones, explicitly: they
  are not tied to the common model by a relationship, and PostgreSQL checks the foreign key at once.
- **Guest identity.** The browser makes a random UUID once, keeps it in localStorage and sends it when joining. It is
  stored in `game_players.guest_id` and never sent to other players. It names a browser, not a person.
- **Statistics for a player.** `GET /api/me/stats/{game}` returns one game's numbers for the browser that asks
  (its guest id, sent in a header). For the bomb game: totals, activity, the words played most with their meaning
  and an example, and the last ten. With accounts the same view will be computed over every linked browser.
- **Accounts.** Guest or account: playing as a guest stays the default and stays complete. An account is a username,
  a password (Argon2id, hashed off the event loop) and an optional email; sign-up is protected by a captcha
  (Cloudflare Turnstile, free) and rate limits, and there is no activation step to play. Sign-in is a random secret in
  an httpOnly, SameSite=Lax cookie (Secure in production); the database keeps only its hash (`login_sessions`).
  Unknown user and wrong password give the same answer and take the same time, and a username is locked after ten
  wrong guesses in 15 minutes. Signing up or in hands over the browser's guest id: it is recorded in
  `player_guests`, and `game_players.player_id` is filled for that browser's past games. Statistics read through
  `player_guests`, so every device the person signs in on shows the same history. A browser already linked to one
  account cannot be claimed by another. A player deletes their own account from the Account page: the login,
  sessions and links are erased, and the past games stay with nobody attached.
- **E-mail confirmation.** The address is required at sign-up and confirmed by a link: a random secret in a message
  (`app/mail`), stored only as a hash in `email_tokens`, valid 24 hours, single use, and tied to the address it was sent
  to (changing the address makes it useless). Sending happens in the background: no mail server, or a failing one,
  never blocks or fails a sign-up. "Send again" is limited to 3 per hour per account. The link opens a page that
  posts the secret (a link scanner that only reads the page confirms nothing).
- **Next for accounts.** Password reset by email once the address is confirmed (the confirmation itself exists), and "Sign in with Google". Apple is left out: it
  needs a paid developer account. Ranks, leaderboards and friends build on `player_id`.
- **Only what is needed.** No IP address, no device information, no tracking cookie. What is stored is described to
  players on the credits page.
- **Operations.** Migrations only add, are applied by `deploy.sh` before the new version starts, and a failure stops the
  deployment untouched. Daily dumps, 14 days, with a tested restore (docs/DEPLOY.md).
