from typing import Any

import structlog
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.prebuilt import ToolNode

from travel_assistant.agent.prompts import SYSTEM_PROMPT
from travel_assistant.agent.state import AgentState
from travel_assistant.agent.tools import all_tools
from travel_assistant.config import get_settings
from travel_assistant.observability.metrics import llm_tokens_total
from travel_assistant.persistence.database import get_session
from travel_assistant.persistence.models import MessageRole
from travel_assistant.persistence.repositories import append_message

logger = structlog.get_logger(__name__)

_llm: ChatAnthropic | None = None
_tool_node: ToolNode | None = None


def _get_llm() -> ChatAnthropic:
    global _llm
    if _llm is None:
        settings = get_settings()
        _llm = ChatAnthropic(
            model=settings.llm.model,
            api_key=settings.llm.api_key,
            streaming=True,
        )
    return _llm


def _get_tool_node() -> ToolNode:
    global _tool_node
    if _tool_node is None:
        _tool_node = ToolNode(all_tools)
    return _tool_node


async def call_agent(state: AgentState) -> dict[str, Any]:
    """Invoke the LLM with bound tools and the current message history."""
    llm = _get_llm().bind_tools(all_tools)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, *state["messages"]]
    response = await llm.ainvoke(messages)

    if hasattr(response, "usage_metadata") and response.usage_metadata:
        usage = response.usage_metadata
        if getattr(usage, "input_tokens", None):
            llm_tokens_total.labels(kind="input").inc(usage.input_tokens)
        if getattr(usage, "output_tokens", None):
            llm_tokens_total.labels(kind="output").inc(usage.output_tokens)

    return {"messages": [response]}


async def call_tools(state: AgentState) -> dict[str, Any]:
    """Execute all tool calls in the last AI message and detect escalation."""
    result = await _get_tool_node().ainvoke(state)

    last_ai = state["messages"][-1]
    tool_calls = getattr(last_ai, "tool_calls", []) or []

    updates: dict[str, Any] = {**result}
    for tc in tool_calls:
        if tc["name"] == "escalate_to_human":
            updates["requires_escalation"] = True
            updates["escalation_reason"] = tc["args"].get("reason", "unspecified")
            logger.info("escalation triggered", reason=updates["escalation_reason"])
            break

    return updates


async def persist(state: AgentState) -> dict[str, Any]:
    """Write the latest human and assistant messages to the database."""
    messages = state["messages"]
    session_id = state["session_id"]

    # The graph only reaches this node when agent produced a response with no tool calls,
    # so the last AIMessage without tool_calls is the final response for this turn.
    last_ai = next(
        (m for m in reversed(messages) if isinstance(m, AIMessage) and not m.tool_calls),
        None,
    )
    last_human = next(
        (m for m in reversed(messages) if isinstance(m, HumanMessage)),
        None,
    )

    try:
        async with get_session() as session:
            if last_human is not None:
                content = (
                    last_human.content
                    if isinstance(last_human.content, str)
                    else str(last_human.content)
                )
                await append_message(session, session_id, MessageRole.user, content)
            if last_ai is not None:
                content = (
                    last_ai.content if isinstance(last_ai.content, str) else str(last_ai.content)
                )
                await append_message(session, session_id, MessageRole.assistant, content)
    except Exception:
        logger.exception("failed to persist messages", session_id=str(session_id))

    return {}


def route_agent(state: AgentState) -> str:
    """Route to 'tools' if the last AI message has tool calls, otherwise to 'persist'."""
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        return "tools"
    return "persist"


def check_escalation(state: AgentState) -> str:
    """Route after persist; both paths end the graph but the escalation flag is set in state."""
    return "escalate" if state.get("requires_escalation") else "end"
