# Contribuer

## Règles

- Code, commentaires, commits et documentation technique en **anglais**. Interface en français.
- **Conventional Commits**, un commit par changement logique (`feat(engine): ...`, `fix(web): ...`).
- Avant chaque commit : `pnpm lint`, `pnpm typecheck` et `pnpm test` verts. `pre-commit install` automatise cela.
- Le moteur de jeu (`apps/server/app/games`) et le module japonais n'importent ni FastAPI, ni Redis, ni SQLAlchemy.
  Un test l'impose.
- Le serveur décide de tout. Aucune règle de jeu dans le navigateur.
- Types TypeScript du protocole : générés (`pnpm protocol`), jamais écrits à la main.
- Interface : pas d'emoji, pas de dégradé, pas de lueur ni de flou décoratif, ombres dures, contours épais, une seule
  animation continue (la mèche). Chaque changement visuel est vérifié avec `/design` et `scripts/shots.mjs`.
- Décision d'architecture non triviale : ajoute une note courte dans `docs/ADR/`.

## Pièges connus

- SvelteKit 3 : alias `#lib/...` (pas `$lib`) avec extension explicite pour les fichiers `.ts`.
- Ne nomme pas une classe CSS `ring`, `container`, `card`... sans vérifier qu'elle n'entre pas en collision avec un
  utilitaire Tailwind.
- Les tests de charge et de simulation sont longs : `HAJIME_SIM_GAMES` règle le nombre de parties simulées.
