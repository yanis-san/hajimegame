# 0005 SvelteKit 3 conventions

Status: accepted. SvelteKit 3 replaces `$lib` by `#lib` (package.json `imports`), which TypeScript only resolves
with an explicit extension for `.ts` files. Public configuration uses Vite's `VITE_API_URL` (fixed at build time)
instead of the new `$app/env` system to keep the setup simple. In development a Vite proxy makes the game server
same-origin; in production either put both behind one domain (Caddyfile) or build with `VITE_API_URL`.
