# Hajime Game

A free multiplayer browser game for learners of Japanese: find a Japanese word before the bomb explodes.

- **Two modes.** *Classic*: the prompt is a short kana fragment and your word must contain it. *Shiritori*: your word
  must start with the last kana of the previous one.
- **2 to 8 players** on phone or desktop, **no account needed**: pick a nickname and an avatar and share the link. An optional account (username and
  password) keeps your history and statistics on all your devices. You can
  also play against CPU players (easy, normal, hard).
- **Learn as you play.** Every accepted word shows its meaning in English (and French when the dictionary has it) and,
  for many words, an example sentence. After a game you can review every word, and the last 10 games are kept on your
  device. A statistics page shows the words you play most (with meanings and examples), your last words, and
  your totals, per game mode.
- **Three interface languages** (French, English, Japanese), chosen by the URL (`/en`, `/ja`), so a shared link always
  opens in its own language. Players in the same room can each use a different one.
- **Fair and fast.** The server is authoritative (FastAPI, WebSocket), the interface is SvelteKit (Svelte 5).

## Quick start (Windows, macOS, Linux)

Requirements: [uv](https://docs.astral.sh/uv/) (Python), [Node.js](https://nodejs.org) 24+ and pnpm
(`npm i -g pnpm`). Docker is optional: the game runs without a database and without Redis. With PostgreSQL it stores finished
games (see `.env.example`).

```bash
git clone https://github.com/yanis-san/hajimegame.git && cd hajimegame
pnpm install
pnpm bootstrap   # installs the Python dependencies and the test browser
pnpm dev         # game server on :8000 + web app on :5173
```

Open <http://localhost:5173>, create a game, then open the invitation link in a second tab (or on your phone, with the
network address Vite prints).

## Commands

| Command | What it does |
| --- | --- |
| `pnpm dev` | Runs the server and the web app with live reload |
| `pnpm test` | Server tests (pytest) and web unit tests (vitest) |
| `pnpm lint` | ruff, mypy, eslint, prettier, and a check that the protocol types are up to date |
| `pnpm typecheck` | Strict mypy and svelte-check |
| `pnpm e2e` | Whole games in real browsers (desktop and mobile). `E2E_PREVIEW=1` tests the production build |
| `pnpm build` | Production build of the web app |
| `pnpm protocol` | Regenerates the TypeScript types from the server protocol |
| `pnpm dictionary` | Rebuilds the dictionary from JMdict (downloads the source files) |
| `pnpm load` | Load test: 200 rooms of 6 players |

On Linux and macOS, `make dev`, `make test`, etc. do the same. The task runner is `tools/tasks.ts`, plain TypeScript
run by Node.

## Project layout

```text
apps/server        FastAPI: pure game engine, rooms, WebSocket, Japanese text handling
apps/web           SvelteKit: home, lobby, game, results, history, /design component page
packages/protocol  JSON schema and generated TypeScript types
tools/             build_dictionary.py, gen_protocol.py, loadtest.py, tasks.ts
docs/              ARCHITECTURE, PROTOCOL, DICTIONARY, DEPLOY, ADDING_A_GAME, ADR/
deploy/            production stack (Compose, Caddy), deployment scripts, Fly.io examples
.github/           CI/CD, security scans, Dependabot
```

## Quality

| What | Result |
| --- | --- |
| Server | 218 tests, strict `mypy` and `ruff`, coverage reported in CI |
| Game engine | 10 000 simulated bot games per CI run, invariants checked after every move |
| Web | 43 unit tests, `svelte-check` and `eslint` clean |
| End to end | 42 browser tests (desktop and mobile) on the production build, including accessibility checks and a strict Content-Security-Policy that blocks injected scripts |
| Word validation | about 3 µs per word (budget 50 µs) |

## Deploying

A push to `main` is tested, built into hardened container images, scanned, published, deployed to your server over SSH
and smoke-tested, with an automatic rollback if the new version is not healthy. One command prepares the server and
the GitHub repository (`deploy/provision.sh`). See [docs/DEPLOY.md](docs/DEPLOY.md).

## Licence and credits

Hajime Game is free and its **code is open source under the [MIT licence](LICENSE)**: you may use, modify and
redistribute it, keeping the copyright notice. © 2026 yanis-san.

The game relies on data and fonts that are **not** under the MIT licence and keep their own. They are also shown to
players on the game's "Credits and licences" page.

| What | Licence |
| --- | --- |
| Source code (server, web app, tools) | [MIT](LICENSE) |
| Dictionary: [JMdict](https://www.edrdg.org/jmdict/j_jmdict.html), © Electronic Dictionary Research and Development Group | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). The compiled file is an adaptation of it and stays under the same licence |
| Example sentences and their translations: [Tatoeba](https://tatoeba.org) and its contributors | [CC BY 2.0 FR](https://creativecommons.org/licenses/by/2.0/fr/) |
| Fonts: JetBrains Mono, Shippori Mincho, Zen Kaku Gothic New, Zen Maru Gothic | SIL Open Font Licence 1.1 |
| Dependencies (npm, Python) | their own licences, mostly MIT, BSD and Apache-2.0 |

Details are in [NOTICE.md](NOTICE.md); how the dictionary is built is in [docs/DICTIONARY.md](docs/DICTIONARY.md).
