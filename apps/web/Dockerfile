# Build context is the repository root: docker build -f apps/web/Dockerfile .
FROM node:24-slim AS build
RUN corepack enable
WORKDIR /repo
COPY pnpm-workspace.yaml package.json pnpm-lock.yaml ./
COPY packages/protocol packages/protocol
COPY apps/web apps/web
RUN pnpm install --frozen-lockfile
ARG VITE_API_URL=
ENV VITE_API_URL=$VITE_API_URL
RUN pnpm --filter web build

FROM node:24-slim
WORKDIR /app
ENV NODE_ENV=production PORT=3000
COPY --from=build /repo/apps/web/build ./build
COPY --from=build /repo/apps/web/package.json ./
USER node
EXPOSE 3000
CMD ["node", "build"]
