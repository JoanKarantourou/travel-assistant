"""Shared HTTP client for all external provider calls.

A single ``httpx.AsyncClient`` instance is reused across requests so that
connections to third-party APIs are pooled rather than opened per-call.
"""

import httpx

_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    """Return the singleton ``AsyncClient``, creating it on first call."""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=10.0)
    return _client


async def close_http_client() -> None:
    """Close and release the shared HTTP client (call on application shutdown)."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
