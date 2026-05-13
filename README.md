# Travel Assistant

A conversational travel assistant that helps users search for flights and hotels, check weather
forecasts, convert currencies, and answer travel-related questions from an FAQ knowledge base.
Built on LangGraph for agent orchestration, Chainlit for the chat UI, and Postgres with pgvector
for persistence and semantic search. The assistant can create bookings (persisted locally),
escalate to a human agent when needed, and resume conversations across sessions.

## Architecture

Each user message enters a LangGraph agent loop. The `agent` node calls Claude with the full
message history and a set of bound tools. If the model produces tool calls, control passes to
the `tools` node, which executes them and returns results to the agent for another LLM pass.
Once the model produces a plain text response (no tool calls), the `persist` node writes the
turn to Postgres, and the graph ends. If the `escalate_to_human` tool was called at any point,
the final state carries `requires_escalation=True` and the Chainlit UI renders a handoff card.

Providers (weather, exchange, flights, hotels) are called through async HTTP clients or the
mock Amadeus implementation. FAQ retrieval uses pgvector nearest-neighbour search over
sentence-transformer embeddings stored in the `faq_chunks` table. Structured logging, Prometheus
metrics, and OpenTelemetry traces are emitted on every agent turn and tool call.

## Stack

- Python 3.12, managed with uv
- Postgres 16 + pgvector
- Chainlit (chat UI)
- LangGraph (agent graph)
- Anthropic Claude (model configured via `ANTHROPIC_MODEL` env var)
- SQLAlchemy 2.x async + asyncpg, Alembic
- sentence-transformers (local embeddings, all-MiniLM-L6-v2)
- Prometheus + OpenTelemetry + Jaeger + Grafana

## Setup

Prerequisites: uv, Docker Desktop, an Anthropic API key.

```
cp .env.example .env
# fill in ANTHROPIC_API_KEY (and DB_PASSWORD if changed from the default)
docker compose up -d postgres jaeger prometheus grafana otel-collector
uv sync
uv run alembic upgrade head
# place src/travel_assistant/data/faqs.pdf, then:
uv run python scripts/seed_faqs.py
```

## Run

Dev (hot reload):

```
uv run chainlit run src/travel_assistant/app.py -w
```

Full stack (app in container):

```
docker compose up app
```

UI available at http://localhost:8000. Grafana at http://localhost:3000, Jaeger at
http://localhost:16686.

## Tests

```
uv run pytest -q
```

Integration tests require a running Postgres and the `RUN_INTEGRATION_TESTS=1` env var:

```
RUN_INTEGRATION_TESTS=1 uv run pytest -q
```

## Project layout

```
src/travel_assistant/
  agent/            LangGraph graph, nodes, tools, prompts, state
  providers/        weather, exchange, flights, hotels (mock Amadeus)
  rag/              FAQ ingest, chunking, pgvector retrieval
  persistence/      SQLAlchemy models, async repositories, Alembic
  services/         booking, chat history, escalation helpers
  observability/    structlog, Prometheus metrics, OTel tracing
tests/
  unit/
  integration/
scripts/            seed helpers (seed_faqs.py, seed_bookings.py)
infra/              OTel collector, Prometheus, Grafana configs
alembic/            migration scripts
```

## Notes

Flights and hotels use a mock Amadeus provider. The Amadeus self-service API is being
decommissioned in July 2026; this codebase ships a local mock that mirrors the Amadeus REST
response shape so behaviour is deterministic without an external dependency. To wire a real
provider, implement the `FlightProvider` or `HotelProvider` protocol defined in
`src/travel_assistant/providers/base.py` and swap the factory return value in
`providers/flights.py` or `providers/hotels.py`.
