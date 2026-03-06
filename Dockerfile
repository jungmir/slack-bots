# ---------- build stage ----------
FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies first (layer cache)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy source and install project
COPY src/ src/
RUN uv sync --frozen --no-dev

# ---------- runtime stage ----------
FROM python:3.13-slim

WORKDIR /app

# Copy virtual environment and source from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

ENV PATH="/app/.venv/bin:$PATH"

# Default data directory for SQLite (mount Railway Volume here)
ENV DATA_DIR=/app/data

EXPOSE 8080

CMD ["python", "-m", "src"]
