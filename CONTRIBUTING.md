# Contributing

## Rules

- Code, comments, commits and technical documentation in **English**. The interface is translated (French, English,
  Japanese); a new message goes in all three files of `apps/web/src/lib/i18n/`.
- **Conventional Commits**, one commit per logical change (`feat(engine): ...`, `fix(web): ...`). Do not add
  co-author or tool attribution lines.
- Before each commit, `pnpm lint`, `pnpm typecheck` and `pnpm test` must be green. `pre-commit install` automates it.
- The game engine (`apps/server/app/games`) and the Japanese module import neither FastAPI, Redis nor SQLAlchemy.
  A test enforces it.
- The server decides everything. No game rule lives in the browser.
- The protocol's TypeScript types are generated (`pnpm protocol`), never written by hand.
- TypeScript everywhere in the web app and the tooling; Python for the server. Config and task files are `.ts` too.
- Interface: no emoji, no gradients, no glow or decorative blur, hard shadows, thick outlines, and a single continuous
  animation (the fuse). Check every visual change on the `/design` page.
- A non-trivial architecture decision gets a short note in `docs/ADR/`.
- Never commit personal notes, credentials or `.env` files (the repository ignores the usual ones).

## Known pitfalls

- SvelteKit 3: use the `#lib/...` alias (not `$lib`) with an explicit extension for `.ts` files.
- Do not name a CSS class `ring`, `container`, `card`... without checking that it does not collide with a Tailwind
  utility.
- Load and simulation tests are long: `HAJIME_SIM_GAMES` sets the number of simulated games.
- End-to-end tests start their own servers; on a manually started game server, raise the rate limits
  (`HAJIME_MAX_ROOMS_PER_IP`, `HAJIME_ROOM_CREATIONS_PER_MINUTE`, `HAJIME_JOIN_ATTEMPTS_PER_MINUTE`) or they fail
  at random.
