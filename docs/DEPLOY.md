# Deploying Hajime

Everything after `git push` is automatic: the pipeline tests the code, builds and scans the container images,
publishes them, deploys them to your server, tests the live site, and puts the previous version back by itself if
the new one does not become healthy. This page is the one-time setup and the runbook.

## What you get

```
git push main
  └─ CI/CD workflow (.github/workflows/ci.yml)
       server ── lint, types, 10 000 simulated games, protocol check
       web ───── lint, types, unit tests, build
       e2e ───── 40+ browser tests against the PRODUCTION build (strict Content-Security-Policy)
       containers (server, web) ── Dockerfile lint · build · vulnerability scan · start, healthy, non-root
       deploy-config ── compose file, Caddyfile and shell scripts are valid
       publish ─ images to GHCR tagged with the commit hash, with SBOM and signed provenance
       deploy ── (when DEPLOY_ENABLED) ssh · pull · wait for quiet · start · health checks · rollback if needed
                 then deploy/smoke.py tests the live site from outside
  Security workflow (.github/workflows/security.yml): CodeQL, dependency review, audits, secret scan (weekly too)
  Dependabot: weekly pull requests for dependencies, GitHub Actions (pinned by hash) and image digests
```

One small server runs three containers: **Caddy** (the only public one: HTTPS certificate obtained and renewed by
itself, HTTP/2 and HTTP/3, security headers), the **web app** and the **game server**. See `deploy/compose.prod.yml`.

## One-time setup (about 15 minutes)

You need a server (any VPS with Ubuntu 24.04 or Debian 12, 1 vCPU and 2 GB of memory is enough: the game server
uses about 400 MB) and a domain name.

1. **Create an SSH key for the pipeline** (on your computer, no passphrase, used only for this):
   `ssh-keygen -t ed25519 -f hajime-deploy -N "" -C hajime-pipeline`
2. **Prepare the server.** Copy `deploy/bootstrap-server.sh` to it and run, as root:
   `bash bootstrap-server.sh "$(cat hajime-deploy.pub)" hajime.yourdomain.com you@yourmail.com ghcr.io/<github-user>/<repo>`
   It installs Docker, creates the `deploy` user, opens only ports 22, 80 and 443, enables automatic security
   updates and fail2ban, and writes `/opt/hajime/.env` (with a generated metrics token). It prints the value for
   `DEPLOY_KNOWN_HOSTS` at the end (replace `<server-address>` with the address you will use in `DEPLOY_HOST`).
3. **DNS:** point `hajime.yourdomain.com` (A, and AAAA if you have IPv6) to the server.
4. **GitHub**, repository *Settings → Secrets and variables → Actions*:

   | Kind | Name | Value |
   | --- | --- | --- |
   | secret | `DEPLOY_HOST` | the server address |
   | secret | `DEPLOY_USER` | `deploy` |
   | secret | `DEPLOY_SSH_KEY` | the **private** key (`hajime-deploy`) |
   | secret | `DEPLOY_KNOWN_HOSTS` | the line printed by the bootstrap script |
   | variable | `DEPLOY_DOMAIN` | `hajime.yourdomain.com` |
   | variable | `DEPLOY_ENABLED` | `true` (until then, a push only tests and publishes) |

5. **Recommended:** *Settings → Environments → production → Required reviewers* adds a one-click approval before
   each deployment. *Settings → Branches* can require the CI checks before merging to `main`.
6. **Push to `main`.** The first deployment also obtains the certificate (it can take a minute).
7. Once SSH works with your key: `HARDEN_SSH=1 sudo -E bash bootstrap-server.sh ...` turns off password logins.

## Every day

- **Deploy:** merge to `main`. Nothing else.
- **Roll back:** *Actions → Deploy a specific version → Run workflow*, with the commit hash of a version that was
  published before. The server also rolls back by itself when a new version fails its health checks.
- **Watch it:** `docker compose -f /opt/hajime/compose.prod.yml logs -f --tail 100` on the server (JSON logs, rotated).
  `/healthz` and `/readyz` are public; `/metrics` (Prometheus) needs `Authorization: Bearer $HAJIME_METRICS_TOKEN`
  from `/opt/hajime/.env` and is never served through Caddy. Set `HAJIME_SENTRY_DSN` in that `.env` for error reports.
- **Updates:** Dependabot pull requests go through the same pipeline; merge them when green.

## Security model

| Layer | What is in place |
| --- | --- |
| Supply chain | Actions pinned by commit hash; base images pinned by digest; lock files enforced (`--frozen`); Dependabot; dependency review on pull requests; weekly audits; image scan (fixable HIGH/CRITICAL fail the build); SBOM and signed build provenance for every image |
| Secrets | Only deployment credentials exist, as GitHub secrets, passed through environment variables (never interpolated into scripts). The registry token reaches the server on stdin and is removed after the deployment. History is scanned for leaked secrets |
| Deployment | The server's SSH key is pinned (no trust on first use); a dedicated `deploy` user and key; one deployment at a time; optional manual approval |
| Edge | Automatic HTTPS, HSTS, HTTP/3; security headers on every response; request bodies capped; `/metrics` never public |
| App | Strict Content-Security-Policy with a nonce per response (tested to block injected scripts), `X-Frame-Options`, `nosniff`, no referrer; origin checks on REST and WebSocket; rate limits; the production server refuses to start with unsafe settings (HTTP or localhost origins, missing origin allowed) |
| Containers | Non-root user, read-only filesystem, all capabilities dropped, `no-new-privileges`, memory and process limits, no published ports except Caddy, health checks, rotated logs |
| Host | Firewall (22, 80, 443), automatic security updates, fail2ban, optional SSH password login off |

There is nothing to back up: the game keeps no database (rooms live in memory, a player's history stays in their
own browser). The only state on the server is the certificate volume (`caddy_data`), which Caddy recreates if lost.

## Know before you rely on it

- **A deployment ends the games in progress**, because rooms live in the game server's memory. `deploy.sh` waits up
  to `DRAIN_SECONDS` (default 180) for the rooms to empty, then deploys anyway. Deploy at quiet hours.
- **One server, one instance.** That is a single point of failure, fine for a game of this size. Several instances
  need Redis (`HAJIME_REDIS_URL`) and a load balancer that keeps a room's connections on its instance
  (see ADR 0003); the Fly.io files (`deploy/fly.*.toml`) sketch that and are **not** part of this pipeline.
- **This pipeline has been written and checked statically, but not run end to end.** Workflows pass `actionlint`,
  scripts pass ShellCheck, the production server and the production web build were started locally under the exact
  settings the containers use, and the browser tests run against the production build. The Docker images, the Caddy
  configuration and the GitHub runs themselves are exercised for the first time by the first push: the `containers`
  and `deploy-config` jobs validate them before anything is published or deployed, so a mistake stops there.
- **Another proxy or CDN in front of Caddy** (Cloudflare, a load balancer) hides the visitors' addresses from the
  rate limits unless Caddy is told to trust it (`trusted_proxies` in `deploy/Caddyfile.prod`). Without one in front,
  the defaults are right.
- Deployment secrets live in the GitHub repository. Anyone who can push to `main` (or approve a deployment) can
  deploy; protect the branch and the `production` environment accordingly.
