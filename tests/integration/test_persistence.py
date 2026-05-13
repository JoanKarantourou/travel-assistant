import uuid

from sqlalchemy import delete

from tests.conftest import skip_no_db
from travel_assistant.persistence.database import get_session
from travel_assistant.persistence.models import ChatSession, MessageRole
from travel_assistant.persistence.repositories import (
    append_message,
    create_chat_session,
    load_messages,
)


@skip_no_db
async def test_chat_message_round_trip():
    customer_name = f"Test User {uuid.uuid4().hex[:8]}"
    chat_session = None
    try:
        async with get_session() as session:
            chat_session = await create_chat_session(session, customer_name=customer_name)
            assert chat_session.id is not None

            await append_message(session, chat_session.id, MessageRole.user, "Hello")
            await append_message(session, chat_session.id, MessageRole.assistant, "Hi there")

        async with get_session() as session:
            messages = await load_messages(session, chat_session.id)

        assert len(messages) == 2
        assert messages[0].role == MessageRole.user
        assert messages[0].content == "Hello"
        assert messages[1].role == MessageRole.assistant
    finally:
        if chat_session and chat_session.id:
            async with get_session() as session:
                await session.execute(
                    delete(ChatSession).where(ChatSession.id == chat_session.id)
                )
                await session.commit()
