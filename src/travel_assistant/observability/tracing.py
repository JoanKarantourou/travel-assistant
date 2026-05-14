"""OpenTelemetry tracing configuration and decorator utilities.

Sets up a ``TracerProvider`` backed by an OTLP gRPC exporter, instruments
httpx and SQLAlchemy automatically, and provides ``track_tool_call`` and
``traced`` decorators for manual span creation.
"""

import asyncio
import functools
import time
from collections.abc import Callable
from typing import TypeVar

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from travel_assistant.config import get_settings

F = TypeVar("F", bound=Callable)

_tracer: trace.Tracer | None = None


def configure_tracing() -> None:
    """Initialise the OTLP tracer provider and auto-instrument httpx and SQLAlchemy."""
    global _tracer
    settings = get_settings()

    resource = Resource(attributes={SERVICE_NAME: settings.observability.otel_service_name})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(endpoint=settings.observability.otel_exporter_otlp_endpoint)
        )
    )
    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer(settings.observability.otel_service_name)

    HTTPXClientInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument()


def get_tracer() -> trace.Tracer:
    """Return the configured tracer, falling back to a no-op tracer before ``configure_tracing`` runs."""
    if _tracer is not None:
        return _tracer
    return trace.get_tracer("travel-assistant")


def track_tool_call(tool_name: str) -> Callable[[F], F]:
    """Decorator that records an OTel span, counter, and duration histogram for a tool call."""

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            from travel_assistant.observability.metrics import (
                tool_call_duration_seconds,
                tool_calls_total,
            )

            start = time.perf_counter()
            status = "success"
            try:
                with get_tracer().start_as_current_span(f"tool.{tool_name}"):
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


def traced(span_name: str | None = None) -> Callable[[F], F]:
    """Decorator that wraps a function in an OTel span."""

    def decorator(fn: F) -> F:
        name = span_name or fn.__qualname__
        if asyncio.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapper(*args, **kwargs):
                with get_tracer().start_as_current_span(name):
                    return await fn(*args, **kwargs)

            return async_wrapper  # type: ignore[return-value]
        else:

            @functools.wraps(fn)
            def sync_wrapper(*args, **kwargs):
                with get_tracer().start_as_current_span(name):
                    return fn(*args, **kwargs)

            return sync_wrapper  # type: ignore[return-value]

    return decorator
