# syntax=docker/dockerfile:1.7
# Web app (SvelteKit, adapter-node). The build context is the repository root:
#   docker build -f apps/web/Dockerfile .
# Base images are pinned by digest (see apps/server/Dockerfile).

FROM node:24-slim@sha256:dc26ae92c9fb15cf6b1d63e20f0944b2efe0f115b20e00be48fb23fceb061c54 AS build
RUN corepack enable
WORKDIR /repo
# dependencies first: this layer is rebuilt only when a manifest or the lock file changes
COPY pnpm-workspace.yaml package.json pnpm-lock.yaml ./
COPY packages/protocol/package.json packages/protocol/
COPY apps/web/package.json apps/web/
RUN pnpm install --frozen-lockfile
COPY packages/protocol packages/protocol
COPY apps/web apps/web
# Empty = same origin (the reverse proxy sends /api and /ws to the game server). Set it at build time only
# when the game server lives on another origin, and allow that origin in HAJIME_ALLOWED_ORIGINS.
ARG VITE_API_URL=
ENV VITE_API_URL=$VITE_API_URL
RUN pnpm --filter web build

FROM node:24-slim@sha256:dc26ae92c9fb15cf6b1d63e20f0944b2efe0f115b20e00be48fb23fceb061c54 AS runtime
WORKDIR /app
# The app only needs `node`. The package managers that ship with the base image (npm, yarn, corepack) are never
# used at runtime and carry their own vulnerabilities, so they are removed: less to patch, less to attack.
RUN rm -rf /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/corepack \
    /usr/local/bin/npm /usr/local/bin/npx /usr/local/bin/corepack \
    /usr/local/bin/yarn /usr/local/bin/yarnpkg /opt/yarn-*
# adapter-node bundles its dependencies: the build folder is all the app needs, no node_modules
ENV NODE_ENV=production PORT=3000
COPY --from=build --chown=node:node /repo/apps/web/build ./build
COPY --chown=node:node apps/web/package.json ./
USER node
EXPOSE 3000
HEALTHCHECK --interval=15s --timeout=4s --start-period=15s --retries=3 \
  CMD ["node", "-e", "fetch('http://127.0.0.1:3000/up').then((r) => process.exit(r.ok ? 0 : 1)).catch(() => process.exit(1))"]
STOPSIGNAL SIGTERM
CMD ["node", "build"]
