# syntax=docker/dockerfile:1.7
# Game server. The build context is the repository root:  docker build -f apps/server/Dockerfile .
#
# Base images are pinned by digest so a build is reproducible and a replaced tag cannot slip in; Dependabot
# proposes the new digests. The server uses no database today (rooms live in memory, or in Redis when
# HAJIME_REDIS_URL is set), so the container only starts the web server: there is no migration step.

FROM python:3.15-slim-bookworm@sha256:96599df822d0e1c6bb700014a05c7f3c8cabc6e0f7ff3c4f9f69cee033b4b5d9 AS build
COPY --from=ghcr.io/astral-sh/uv:0.13@sha256:96f40d3904aad8d0bd010539001d36c8e2188b981e1334471a90c4a1d93bb490 /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
# dependencies first: this layer is rebuilt only when the lock file changes
COPY apps/server/pyproject.toml apps/server/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY apps/server/app ./app
# `alembic upgrade head` runs from this image at deployment time (see deploy/deploy.sh)
COPY apps/server/alembic.ini ./

FROM python:3.15-slim-bookworm@sha256:96599df822d0e1c6bb700014a05c7f3c8cabc6e0f7ff3c4f9f69cee033b4b5d9 AS runtime
# The system pip, setuptools and wheel are build tools: the app runs from its own virtualenv and never needs them,
# so they are removed (they and the libraries pip vendors are a regular source of vulnerability reports).
RUN groupadd --gid 10001 hajime \
 && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin hajime \
 && rm -rf /usr/local/lib/python3.13/site-packages/pip* /usr/local/lib/python3.13/site-packages/setuptools* \
    /usr/local/lib/python3.13/site-packages/wheel* /usr/local/lib/python3.13/site-packages/pkg_resources \
    /usr/local/lib/python3.13/site-packages/_distutils_hack /usr/local/bin/pip /usr/local/bin/pip3 \
    /usr/local/bin/pip3.13 /usr/local/bin/wheel
WORKDIR /app
COPY --from=build --chown=10001:10001 /app /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HAJIME_ENV=prod
USER 10001:10001
EXPOSE 8000
# /readyz is 503 until the dictionary and the CPU index are loaded (a few seconds), hence the start period
HEALTHCHECK --interval=15s --timeout=4s --start-period=40s --retries=3 \
  CMD ["python", "-c", "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/readyz', timeout=3)"]
STOPSIGNAL SIGTERM
# The proxy (Caddy) is the only thing that reaches this port: it says which scheme and address the visitor used
# (X-Forwarded-Proto/For), and the server must believe it, or the admin writes http:// links on an https:// site.
# Exec form: uvicorn is PID 1 and receives SIGTERM, then closes the rooms cleanly (graceful shutdown).
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", \
     "--ws-ping-interval", "20", "--ws-ping-timeout", "20", "--timeout-graceful-shutdown", "20", \
     "--ws-max-size", "65536", "--no-server-header", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
