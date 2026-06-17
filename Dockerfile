# Stage 1: Build virtual environment
FROM ghcr.io/astral-sh/uv:python3.12-alpine AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app

# Install dependencies first (for docker layer caching)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Copy application source code and sync
ADD . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Stage 2: Runtime image
FROM python:3.12-slim-bookworm
WORKDIR /app

# Copy the application and virtual environment from the builder
COPY --from=builder /app /app
ENV PATH="/app/.venv/bin:$PATH"

# Environment variables
ENV PORT=8005
ENV PYTHONUNBUFFERED=1

EXPOSE 8005

CMD ["fastapi", "run", "app.main:app", "--port", "8005", "--host", "0.0.0.0"]
