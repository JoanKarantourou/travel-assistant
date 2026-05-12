import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage

from travel_assistant.agent.graph import build_graph
from travel_assistant.agent.nodes import check_escalation, route_agent
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


def test_route_agent_goes_to_tools_when_tool_calls_present():
    tc = {"name": "get_weather", "args": {}, "id": "tc1", "type": "tool_call"}
    ai = AIMessage(content="", tool_calls=[tc])
    state = _state(messages=[HumanMessage(content="What is the weather?"), ai])
    assert route_agent(state) == "tools"


def test_route_agent_goes_to_persist_when_no_tool_calls():
    ai = AIMessage(content="The weather is sunny.")
    state = _state(messages=[HumanMessage(content="Hi"), ai])
    assert route_agent(state) == "persist"


def test_check_escalation_routes_to_escalate_when_flag_set():
    state = _state(requires_escalation=True, escalation_reason="payment dispute")
    assert check_escalation(state) == "escalate"


def test_check_escalation_routes_to_end_when_flag_clear():
    state = _state(requires_escalation=False)
    assert check_escalation(state) == "end"


def test_build_graph_compiles():
    graph = build_graph()
    assert graph is not None


@patch("travel_assistant.agent.nodes.append_message", new_callable=AsyncMock)
@patch("travel_assistant.agent.nodes.get_session")
@patch("travel_assistant.agent.nodes._get_llm")
async def test_happy_path_single_turn(mock_get_llm, mock_get_session, mock_append_message):
    """One user message, no tool calls - agent replies and graph ends cleanly."""
    ai_response = AIMessage(content="Hello, how can I help you plan your trip?")
    llm = MagicMock()
    llm.bind_tools.return_value = llm
    llm.ainvoke = AsyncMock(return_value=ai_response)
    mock_get_llm.return_value = llm

    session_mock = AsyncMock()
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session_mock)
    cm.__aexit__ = AsyncMock(return_value=False)
    mock_get_session.return_value = cm

    sid = uuid.uuid4()
    graph = build_graph()
    config = {"configurable": {"thread_id": str(sid)}}
    initial: AgentState = {
        "session_id": sid,
        "customer_name": None,
        "messages": [HumanMessage(content="Hello")],
        "requires_escalation": False,
        "escalation_reason": None,
    }
    result = await graph.ainvoke(initial, config=config)

    assert result["requires_escalation"] is False
    last_msg = result["messages"][-1]
    assert isinstance(last_msg, AIMessage)
    assert last_msg.content == "Hello, how can I help you plan your trip?"


@patch("travel_assistant.agent.nodes.append_message", new_callable=AsyncMock)
@patch("travel_assistant.agent.nodes.get_session")
@patch("travel_assistant.agent.nodes._get_llm")
async def test_escalation_sets_flag(mock_get_llm, mock_get_session, mock_append_message):
    """Calling escalate_to_human should set requires_escalation in final state."""
    tool_call_id = "esc-001"

    ai_with_tool = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "escalate_to_human",
                "args": {"reason": "customer requested human agent"},
                "id": tool_call_id,
                "type": "tool_call",
            }
        ],
    )
    ai_final = AIMessage(content="I've escalated your request. A human agent will be in touch.")

    llm = MagicMock()
    llm.bind_tools.return_value = llm
    llm.ainvoke = AsyncMock(side_effect=[ai_with_tool, ai_final])
    mock_get_llm.return_value = llm

    session_mock = AsyncMock()
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session_mock)
    cm.__aexit__ = AsyncMock(return_value=False)
    mock_get_session.return_value = cm

    sid = uuid.uuid4()
    graph = build_graph()
    config = {"configurable": {"thread_id": str(sid)}}
    initial: AgentState = {
        "session_id": sid,
        "customer_name": None,
        "messages": [HumanMessage(content="I want to speak to a human")],
        "requires_escalation": False,
        "escalation_reason": None,
    }
    result = await graph.ainvoke(initial, config=config)

    assert result["requires_escalation"] is True
    assert result["escalation_reason"] == "customer requested human agent"
