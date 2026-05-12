from typing import Annotated, TypedDict
from uuid import UUID

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    session_id: UUID
    customer_name: str | None
    messages: Annotated[list[AnyMessage], add_messages]
    requires_escalation: bool
    escalation_reason: str | None
