import httpx

from travel_assistant.config import get_settings
from travel_assistant.observability import init_observability


def test_init_observability_does_not_raise():
    init_observability()


def test_metrics_server_started_flag():
    init_observability()
    # _server_started is module-level; import after init to get updated value
    import travel_assistant.observability.metrics as m

    assert m._server_started is True


def test_metrics_endpoint_returns_200():
    init_observability()
    port = get_settings().observability.prometheus_port
    response = httpx.get(f"http://localhost:{port}")
    assert response.status_code == 200
    assert b"# HELP" in response.content


async def test_track_tool_call_success():
    import pytest  # noqa: F401

    from travel_assistant.observability import track_tool_call
    from travel_assistant.observability.metrics import tool_calls_total

    before = tool_calls_total.labels(tool="test_tool", status="success")._value.get()

    @track_tool_call("test_tool")
    async def dummy():
        return 42

    result = await dummy()
    assert result == 42
    after = tool_calls_total.labels(tool="test_tool", status="success")._value.get()
    assert after == before + 1


async def test_track_tool_call_records_error():
    import pytest

    from travel_assistant.observability import track_tool_call
    from travel_assistant.observability.metrics import tool_calls_total

    @track_tool_call("error_tool")
    async def boom():
        raise ValueError("oops")

    before = tool_calls_total.labels(tool="error_tool", status="error")._value.get()
    with pytest.raises(ValueError):
        await boom()
    after = tool_calls_total.labels(tool="error_tool", status="error")._value.get()
    assert after == before + 1
