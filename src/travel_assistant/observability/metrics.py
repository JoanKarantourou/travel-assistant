"""Prometheus metrics definitions and HTTP server startup for the travel assistant.

Declares all counters and histograms used across the application and exposes them
on a configurable port for scraping.
"""

from prometheus_client import Counter, Histogram, start_http_server

from travel_assistant.config import get_settings

agent_turns_total = Counter(
    "agent_turns_total",
    "Total agent turns by outcome",
    ["outcome"],
)

agent_turn_duration_seconds = Histogram(
    "agent_turn_duration_seconds",
    "Wall-clock duration of a single agent turn",
)

tool_calls_total = Counter(
    "tool_calls_total",
    "Total tool invocations",
    ["tool", "status"],
)

tool_call_duration_seconds = Histogram(
    "tool_call_duration_seconds",
    "Wall-clock duration of a tool call",
    ["tool"],
)

llm_tokens_total = Counter(
    "llm_tokens_total",
    "Total LLM tokens consumed",
    ["kind"],  # input | output
)

escalations_total = Counter(
    "escalations_total",
    "Total escalations to a human agent",
    ["reason"],
)

_server_started = False


def start_metrics_server() -> None:
    """Start the Prometheus HTTP scrape server on the configured port, at most once."""
    global _server_started
    if not _server_started:
        port = get_settings().observability.prometheus_port
        start_http_server(port)
        _server_started = True
