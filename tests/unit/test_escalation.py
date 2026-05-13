import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage

from travel_assistant.agent.nodes import call_tools, check_escalation
from travel_assistant.agent.state import AgentState


def _state(**overrides) -> AgentState:
    base: AgentState = {  # type: ignore[assignment]
        "session_id": uuid.uuid4(),
        "customer_name": None,
        "messages": [],
        "requires_escalation": False,
        "escalation_reason": None,
    }
    base.update(overrides)  # type: ignore[arg-type]
    return base


async def test_escalate_to_human_tool_returns_escalated_json():
    from travel_assistant.agent.tools import escalate_to_human

    result = await escalate_to_human.ainvoke({"reason": "payment dispute"})
    data = json.loads(result)
    assert data["escalated"] is True
    assert data["reason"] == "payment dispute"


async def test_escalate_to_human_tool_preserves_reason_verbatim():
    from travel_assistant.agent.tools import escalate_to_human

    reason = "complex multi-leg corporate itinerary"
    result = await escalate_to_human.ainvoke({"reason": reason})
    assert json.loads(result)["reason"] == reason


@patch("travel_assistant.agent.nodes._get_tool_node")
async def test_call_tools_sets_escalation_flag_and_reason(mock_get_tool_node):
    tool_node = MagicMock()
    tool_node.ainvoke = AsyncMock(return_value={"messages": []})
    mock_get_tool_node.return_value = tool_node

    ai = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "escalate_to_human",
                "args": {"reason": "user requested human"},
                "id": "tc1",
                "type": "tool_call",
            }
        ],
    )
    state = _state(messages=[HumanMessage(content="I want a human"), ai])
    updates = await call_tools(state)

    assert updates["requires_escalation"] is True
    assert updates["escalation_reason"] == "user requested human"


@patch("travel_assistant.agent.nodes._get_tool_node")
async def test_call_tools_does_not_set_flag_for_non_escalation_tool(mock_get_tool_node):
    tool_node = MagicMock()
    tool_node.ainvoke = AsyncMock(return_value={"messages": []})
    mock_get_tool_node.return_value = tool_node

    ai = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "get_weather",
                "args": {"latitude": 48.8, "longitude": 2.3, "start_date": "2025-07-01", "end_date": "2025-07-02"},
                "id": "tc2",
                "type": "tool_call",
            }
        ],
    )
    state = _state(messages=[HumanMessage(content="weather in Paris?"), ai])
    updates = await call_tools(state)

    assert not updates.get("requires_escalation", False)


def test_check_escalation_routes_to_escalate_when_set():
    state = _state(requires_escalation=True, escalation_reason="visa issue")
    assert check_escalation(state) == "escalate"


def test_check_escalation_routes_to_end_when_clear():
    state = _state(requires_escalation=False)
    assert check_escalation(state) == "end"


def test_check_escalation_treats_missing_flag_as_false():
    state = _state()
    del state["requires_escalation"]  # type: ignore[misc]
    assert check_escalation(state) == "end"
