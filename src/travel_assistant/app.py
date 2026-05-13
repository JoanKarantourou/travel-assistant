import time
import uuid

import chainlit as cl
from langchain_core.messages import HumanMessage

from travel_assistant.agent.graph import build_graph
from travel_assistant.observability.logging import bind_request_id, configure_logging, get_logger
from travel_assistant.observability.metrics import (
    agent_turn_duration_seconds,
    agent_turns_total,
    start_metrics_server,
)
from travel_assistant.observability.tracing import configure_tracing, get_tracer
from travel_assistant.persistence.database import get_session
from travel_assistant.persistence.models import MessageRole
from travel_assistant.persistence.repositories import create_chat_session, load_messages

_graph = build_graph()
_log = get_logger(__name__)


@cl.on_app_startup
async def on_startup() -> None:
    configure_logging()
    configure_tracing()
    start_metrics_server()


@cl.on_chat_start
async def on_chat_start() -> None:
    async with get_session() as db:
        chat_session = await create_chat_session(db)

    session_id = str(chat_session.id)
    cl.user_session.set("session_id", session_id)
    cl.user_session.set("customer_name", None)

    await cl.Message(content="Welcome. How can I help you plan your trip today?").send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    bind_request_id()

    session_id = uuid.UUID(cl.user_session.get("session_id"))
    customer_name: str | None = cl.user_session.get("customer_name")
    config = {"configurable": {"thread_id": str(session_id)}}

    inputs = {
        "session_id": session_id,
        "customer_name": customer_name,
        "messages": [HumanMessage(content=message.content)],
        "requires_escalation": False,
        "escalation_reason": None,
    }

    response_msg = cl.Message(content="")
    start = time.perf_counter()
    outcome = "success"

    with get_tracer().start_as_current_span("agent_turn") as span:
        span.set_attribute("session_id", str(session_id))
        try:
            try:
                async for event in _graph.astream_events(inputs, config=config, version="v2"):
                    if event["event"] != "on_chat_model_stream":
                        continue
                    chunk = event["data"]["chunk"]
                    content = chunk.content
                    if isinstance(content, str) and content:
                        await response_msg.stream_token(content)
                    elif isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                text = block.get("text", "")
                                if text:
                                    await response_msg.stream_token(text)
            except Exception:
                outcome = "error"
                _log.exception("graph stream error", session_id=str(session_id))
                if not response_msg.content:
                    response_msg.content = "Something went wrong on my end. Please try again."

            await response_msg.send()

            final = await _graph.aget_state(config)
            if final.values.get("requires_escalation"):
                outcome = "escalated"
                ticket_id = str(uuid.uuid4())
                reason = final.values.get("escalation_reason") or "unspecified"
                card = (
                    f"**Escalation ticket:** `{ticket_id}`\n"
                    f"**Reason:** {reason}\n\n"
                    "A human agent will review your request and follow up shortly."
                )
                await cl.Message(content=card, type="system_message").send()
        finally:
            agent_turns_total.labels(outcome=outcome).inc()
            agent_turn_duration_seconds.observe(time.perf_counter() - start)


@cl.on_chat_resume
async def on_chat_resume(thread: cl.types.ThreadDict) -> None:
    metadata = thread.get("metadata") or {}
    session_id_str: str | None = metadata.get("session_id")
    if not session_id_str:
        return

    cl.user_session.set("session_id", session_id_str)
    session_id = uuid.UUID(session_id_str)

    async with get_session() as db:
        db_messages = await load_messages(db, session_id)

    for msg in db_messages:
        if msg.role == MessageRole.user:
            await cl.Message(
                content=msg.content,
                type="user_message",
                author="User",
            ).send()
        elif msg.role == MessageRole.assistant:
            await cl.Message(content=msg.content).send()
