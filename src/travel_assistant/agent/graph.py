from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from travel_assistant.agent.nodes import (
    call_agent,
    call_tools,
    check_escalation,
    persist,
    route_agent,
)
from travel_assistant.agent.state import AgentState

# TODO: replace MemorySaver with langgraph-checkpoint-postgres once the package
# is added as a project dependency, so conversation state survives restarts.


def build_graph() -> StateGraph:
    """Compile and return the travel-assistant agent graph."""
    workflow = StateGraph(AgentState)

    workflow.add_node("agent", call_agent)
    workflow.add_node("tools", call_tools)
    workflow.add_node("persist", persist)

    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges(
        "agent",
        route_agent,
        {"tools": "tools", "persist": "persist"},
    )
    workflow.add_edge("tools", "agent")
    workflow.add_conditional_edges(
        "persist",
        check_escalation,
        {"escalate": END, "end": END},
    )

    return workflow.compile(checkpointer=MemorySaver())
