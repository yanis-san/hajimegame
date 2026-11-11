# Hajime Game

Jeu multijoueur en ligne : trouve un mot japonais avant que la bombe explose. Deux modes : Classique (le mot contient
un fragment de kana, difficulté adaptative) et Shiritori (le mot commence par le dernier kana du précédent).
2 à 8 joueurs, sans inscription, sur téléphone ou PC. Serveur autoritaire (FastAPI), interface SvelteKit.

## Démarrer en 5 minutes (Windows, macOS, Linux)

Prérequis : [uv](https://docs.astral.sh/uv/) (Python), [Node.js](https://nodejs.org) 24+ et pnpm (`npm i -g pnpm`).
Docker est facultatif (ni base de données ni Redis ne sont nécessaires pour jouer).

```bash
git clone https://github.com/yanis-san/hajimegame.git && cd hajimegame
pnpm install
pnpm bootstrap      # installe les dépendances Python et le navigateur de test
pnpm dev        # serveur de jeu :8000 + interface :5173
```

Ouvre <http://localhost:5173>, crée une partie, puis ouvre le lien d'invitation dans un second onglet (ou sur ton
téléphone avec l'adresse réseau affichée par Vite). Le guide complet est dans [docs/GUIDE.md](docs/GUIDE.md).

## Commandes

| Commande | Rôle |
| --- | --- |
| `pnpm dev` | Lance serveur et interface avec rechargement automatique |
| `pnpm test` | Tests serveur (pytest) et interface (vitest) |
| `pnpm lint` | ruff, mypy, eslint, prettier, types du protocole à jour |
| `pnpm typecheck` | mypy strict et svelte-check |
| `pnpm e2e` | Parties complètes dans de vrais navigateurs (bureau et mobile) |
| `pnpm build` | Build de production de l'interface |
| `pnpm protocol` | Régénère les types TypeScript depuis le protocole serveur |
| `pnpm dictionary` | Reconstruit le dictionnaire depuis JMdict |
| `pnpm load` | Test de charge : 200 salles de 6 joueurs |

Sous Linux et macOS, `make dev`, `make test`, etc. font la même chose.

## Où est quoi

```text
apps/server   FastAPI : moteur de jeu pur, salles, WebSocket, japonais, base de données
apps/web      SvelteKit : accueil, salle d'attente, partie, résultats, route /design
packages/protocol  Schéma JSON et types TypeScript générés
tools/        build_dictionary.py, gen_protocol.py, loadtest.py, tasks.mjs
docs/         ARCHITECTURE, PROTOCOL, DICTIONARY, GUIDE, DEPLOY (déploiement automatisé), ADR/
deploy/       pile de production (compose, Caddy), scripts de déploiement, exemples Fly.io
```

## Qualité mesurée

| Critère | Résultat |
| --- | --- |
| Tests serveur | 181, couverture 93 %, `mypy --strict` et `ruff` propres |
| Sens des mots | toujours en anglais, et en français en plus quand JMdict le fournit (environ 10 500 mots) |
| Simulation | 10 000 parties de bots, invariants tenus (`make sim`) |
| Validation d'un mot | environ 3 µs (budget : 50 µs) |
| Charge | 200 salles x 6 joueurs, toutes les parties terminées, p95 de traitement environ 5 ms, mémoire stable |
| E2E | 14 scénarios verts (bureau et mobile), axe-core sans violation sérieuse |
| Lighthouse mobile (accueil) | performance 99, accessibilité 100, JS 22 Ko compressé |

## Licences

Code du projet : à définir par l'auteur. Dictionnaire : JMdict, © EDRDG, CC BY-SA 4.0 (voir la page
« Crédits et licences » dans l'application). Polices : SIL OFL 1.1.
