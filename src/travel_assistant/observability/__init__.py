import functools
import time
from collections.abc import Callable
from typing import TypeVar

F = TypeVar("F", bound=Callable)


def init_observability() -> None:
    from travel_assistant.observability.logging import configure_logging
    from travel_assistant.observability.metrics import start_metrics_server
    from travel_assistant.observability.tracing import configure_tracing

    configure_logging()
    configure_tracing()
    start_metrics_server()


def track_tool_call(tool_name: str) -> Callable[[F], F]:
    """Decorator that records a span, latency histogram, and call counter for a tool."""

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            from travel_assistant.observability.metrics import (
                tool_call_duration_seconds,
                tool_calls_total,
            )
            from travel_assistant.observability.tracing import get_tracer

            start = time.perf_counter()
            status = "success"
            with get_tracer().start_as_current_span(f"tool.{tool_name}"):
                try:
                    return await fn(*args, **kwargs)
                except Exception:
                    status = "error"
                    raise
                finally:
                    elapsed = time.perf_counter() - start
                    tool_calls_total.labels(tool=tool_name, status=status).inc()
                    tool_call_duration_seconds.labels(tool=tool_name).observe(elapsed)

        return wrapper  # type: ignore[return-value]

    return decorator
