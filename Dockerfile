# Autometa - Analytics assistant web app

FROM python:3.14-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git procps clamav \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

RUN freshclam --no-dns || true

RUN npm install -g @anthropic-ai/claude-code

RUN useradd -m -s /bin/bash -u 1004 autometa

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.7 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1

COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-editable

COPY --chown=autometa:autometa . .

RUN mkdir -p /app/data/uploads /app/data/modified \
    && chown -R autometa:autometa /app/data /app/.venv

USER autometa

ENV AGENT_BACKEND=sdk \
    WEB_HOST=0.0.0.0 \
    WEB_PORT=5000 \
    WEB_DEBUG=false

EXPOSE 5000

CMD ["./entrypoint.sh"]
