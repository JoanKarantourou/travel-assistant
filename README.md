# Travel Assistant

A conversational travel assistant that helps users search for flights and hotels, check weather forecasts, convert currencies, and answer travel-related questions from an FAQ knowledge base. Built on LangGraph for agent orchestration, Chainlit for the chat UI, and Postgres with pgvector for persistence and semantic search.

The assistant can create bookings (persisted locally), escalate to a human agent when needed, and resume conversations across sessions.

## Stack

- Python 3.12, managed with uv
- Postgres 16 + pgvector
- Chainlit (chat UI)
- LangGraph (agent graph)
- Anthropic Claude (claude-sonnet-4-5)
- SQLAlchemy 2.x async + asyncpg, Alembic
- sentence-transformers (local embeddings, all-MiniLM-L6-v2)
- Prometheus + OpenTelemetry + Jaeger + Grafana

## Setup

- Prerequisites: uv, Docker Desktop, an Anthropic API key
- `cp .env.example .env` and fill in `ANTHROPIC_API_KEY` (and `DB_PASSWORD` if changed)
- `docker compose up -d postgres jaeger prometheus grafana otel-collector`
- `uv sync`
- `uv run alembic upgrade head`
- `uv run python scripts/seed_faqs.py` (place `src/travel_assistant/data/faqs.pdf` first)

## Run

- Dev: `uv run chainlit run src/travel_assistant/app.py -w`
- Full stack: `docker compose up app`

## Tests

- `uv run pytest -q`

## Project layout

```
src/travel_assistant/   main package
  agent/                LangGraph graph, nodes, tools, prompts
  providers/            weather, exchange, flights, hotels (mock Amadeus)
  rag/                  FAQ ingest, chunking, pgvector retrieval
  persistence/          SQLAlchemy models, async repositories, Alembic
  services/             booking, chat history, escalation
  observability/        structlog, Prometheus metrics, OTel tracing
tests/
  unit/
  integration/
scripts/                seed helpers
infra/                  OTel collector, Prometheus, Grafana configs
```

## Notes

- Flights and hotels use a mock Amadeus provider. The Amadeus self-service API is being decommissioned in July 2026; this codebase ships a local mock that mirrors the Amadeus REST response shape. To wire a real provider, implement the `FlightProvider` or `HotelProvider` protocol in `src/travel_assistant/providers/base.py` and swap the factory in `providers/flights.py` and `providers/hotels.py`.
