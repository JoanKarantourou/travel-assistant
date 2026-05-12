import asyncio
import functools
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
    if _tracer is not None:
        return _tracer
    return trace.get_tracer("travel-assistant")


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
