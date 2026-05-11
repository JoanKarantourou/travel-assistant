FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src/ ./src/
RUN uv sync --frozen --no-dev


FROM python:3.12-slim AS runtime

WORKDIR /app

COPY --from=builder /app/.venv ./.venv
COPY --from=builder /app/src ./src

RUN groupadd -g 1000 appgroup \
    && useradd -m -u 1000 -g appgroup appuser \
    && chown -R appuser:appgroup /app

USER appuser

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000 9090

CMD ["chainlit", "run", "src/travel_assistant/app.py", "--host", "0.0.0.0", "--port", "8000"]
