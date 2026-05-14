"""LangGraph state schema for the travel-assistant agent.

``AgentState`` is the single shared data structure that every graph node reads
from and writes to during a conversation turn.
"""

from typing import Annotated, TypedDict
from uuid import UUID

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """Mutable state passed between nodes in the agent graph for one conversation turn."""

    session_id: UUID
    customer_name: str | None
    messages: Annotated[list[AnyMessage], add_messages]
    requires_escalation: bool
    escalation_reason: str | None
