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

## One-time setup (about 10 minutes, one command)

What you need: a **server** (any VPS with Ubuntu 24.04 or Debian 12; 1 vCPU and 2 GB of memory is enough, the game
server uses about 400 MB) and a **domain name** whose DNS you can edit. For a French-speaking audience, pick a
data centre in Europe. You also need the GitHub CLI logged in (`gh auth login`) and `ssh` (both are in Git for
Windows / the GitHub CLI installer).

1. **Create the server** at your provider and note its IP address and the root password (or key) it gives you.
2. **Run one command** from your computer, in the repository (Git Bash on Windows):

   ```bash
   ./deploy/provision.sh root@<server-ip> hajime.yourdomain.com you@yourmail.com
   ```

   It creates the pipeline's SSH key, shows the server's fingerprint for you to compare with your provider's
   console, prepares the server (Docker, a `deploy` user, firewall on ports 22/80/443, automatic security updates,
   fail2ban), checks that the key works, and stores every secret and variable in the GitHub repository. Try
   `--dry-run` first to see exactly what it would do without touching anything.
3. **DNS:** create an `A` record `hajime.yourdomain.com` → the server IP (and `AAAA` for IPv6).
4. **Push:** `git push origin main`. Open the repository's *Actions* tab: when *Deploy to production* is green the
   site is live over HTTPS (the first deployment also obtains the certificate; give it a minute).

Optional, once it works: *Settings → Environments → production → Required reviewers* (one-click approval before
each deployment), *Settings → Branches* (require the CI checks before merging), and `--harden-ssh` on a later run
of `provision.sh` to turn off SSH password logins (only if you log in with a key).

<details>
<summary>What the command does by hand (if you prefer to do it step by step)</summary>

1. `ssh-keygen -t ed25519 -N "" -f ~/.ssh/hajime-deploy -C hajime-pipeline`
2. On the server, as root: `bash bootstrap-server.sh "$(cat hajime-deploy.pub)" <domain> <email> ghcr.io/<user>/<repo>`.
   It prints the line for `DEPLOY_KNOWN_HOSTS` (replace `<server-address>` with the address you use in `DEPLOY_HOST`).
3. GitHub, *Settings → Secrets and variables → Actions*:

   | Kind | Name | Value |
   | --- | --- | --- |
   | secret | `DEPLOY_HOST` | the server address |
   | secret | `DEPLOY_USER` | `deploy` |
   | secret | `DEPLOY_SSH_KEY` | the **private** key |
   | secret | `DEPLOY_KNOWN_HOSTS` | the host key line |
   | variable | `DEPLOY_DOMAIN` | `hajime.yourdomain.com` |
   | variable | `DEPLOY_ENABLED` | `true` (until then a push only tests and publishes) |

4. Create the `production` environment, point the DNS, push.

</details>

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
- **What was tested, and what was not.** Tested with real Docker: both images build; they start, become healthy, run
  as a non-root user without `pip` or `npm`, and pass the vulnerability scan (no fixable HIGH or CRITICAL finding);
  the whole production stack ran locally behind Caddy with HTTPS, and `deploy/smoke.py` passed against it (pages in
  three languages, security headers, `/metrics` closed, a room created, a WebSocket through the proxy);
  `deploy/deploy.sh` was run against a local registry, including the **automatic rollback** of a version that never
  became healthy and the wait for games in progress. Workflows pass `actionlint` and scripts pass ShellCheck.
  **Not exercised yet:** the GitHub runners themselves, publishing to GHCR, the SSH hop to a real server, and the
  Let's Encrypt certificate (the local test used Caddy's own certificate authority). The first real deployment is the
  test of those four; the `containers` and `deploy-config` jobs stop a broken image or configuration before that.
- **Another proxy or CDN in front of Caddy** (Cloudflare, a load balancer) hides the visitors' addresses from the
  rate limits unless Caddy is told to trust it (`trusted_proxies` in `deploy/Caddyfile.prod`). Without one in front,
  the defaults are right.
- Deployment secrets live in the GitHub repository. Anyone who can push to `main` (or approve a deployment) can
  deploy; protect the branch and the `production` environment accordingly.
