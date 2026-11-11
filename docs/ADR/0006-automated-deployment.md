# 0006 Automated deployment: containers, one origin, a single server

Status: accepted. A push to `main` is tested, built into images pinned by digest, scanned, published to GHCR with
provenance, deployed over SSH with a health-checked rollback, and smoke-tested from outside (see `docs/DEPLOY.md`).

- **One origin.** Caddy sends `/api` and `/ws` to the game server and the rest to the web app, so the browser makes
  no cross-origin request: no CORS, WebSockets just work, origin checks stay strict, and the Content-Security-Policy
  needs no third-party origin. This rules out the two-app Fly.io layout for the default path (kept as an example).
- **No database in the deployed stack.** The game keeps nothing between games (a player's history lives in their
  browser), so there is nothing to back up or migrate. The old container start ran `alembic upgrade head || echo`
  against a database that did not exist, hiding any failure; it is gone. Postgres comes back with accounts.
- **One instance on one server.** Rooms live in the memory of one process, so a deployment ends the games in
  progress; `deploy.sh` waits for quiet (bounded) first. Scaling out needs Redis and room-affine routing (ADR 0003).
- **Fail early, in the pipeline.** The production server refuses unsafe settings, the Dockerfiles and the Caddyfile
  are exercised in CI, and the browser tests run against the production build, so a mistake stops before publishing.
- **Secrets stay minimal.** Only SSH credentials exist; they are pinned (host key), scoped to a `deploy` user, passed
  through environment variables, and used behind an optional manual approval.
