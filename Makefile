# Thin wrapper over tools/tasks.ts so `make dev` works on Linux/macOS. On Windows use `pnpm dev`.
.PHONY: bootstrap dev test lint typecheck build e2e protocol dictionary load sim docker-up

bootstrap dev test lint typecheck build e2e protocol dictionary load:
	node tools/tasks.ts $@

# 10 000 simulated games (the default test run plays 1 000)
sim:
	cd apps/server && HAJIME_SIM_GAMES=10000 uv run pytest tests/games/test_simulation.py

docker-up:
	docker compose up --build
