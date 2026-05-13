import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from travel_assistant.persistence.models import (
    Booking,
    BookingStatus,
    ChatMessage,
    ChatSession,
    FAQChunk,
    MessageRole,
)


async def create_chat_session(
    session: AsyncSession, customer_name: str | None = None
) -> ChatSession:
    chat_session = ChatSession(customer_name=customer_name)
    session.add(chat_session)
    await session.flush()
    return chat_session


async def get_chat_session(session: AsyncSession, session_id: uuid.UUID) -> ChatSession | None:
    result = await session.execute(select(ChatSession).where(ChatSession.id == session_id))
    return result.scalar_one_or_none()


async def append_message(
    session: AsyncSession,
    session_id: uuid.UUID,
    role: MessageRole,
    content: str,
    tool_name: str | None = None,
) -> ChatMessage:
    msg = ChatMessage(session_id=session_id, role=role, content=content, tool_name=tool_name)
    session.add(msg)
    await session.flush()
    return msg


async def load_messages(session: AsyncSession, session_id: uuid.UUID) -> list[ChatMessage]:
    result = await session.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    return list(result.scalars().all())


async def find_booking_by_customer_and_dates(
    session: AsyncSession, customer_name: str, start_date: date
) -> Booking | None:
    result = await session.execute(
        select(Booking).where(
            Booking.customer_name == customer_name,
            Booking.start_date == start_date,
        )
    )
    return result.scalar_one_or_none()


async def create_booking(
    session: AsyncSession,
    customer_name: str,
    start_date: date,
    end_date: date,
    destination: str,
    flight_number: str,
    hotel_name: str,
    total_price_eur: Decimal,
) -> Booking:
    booking = Booking(
        customer_name=customer_name,
        start_date=start_date,
        end_date=end_date,
        destination=destination,
        flight_number=flight_number,
        hotel_name=hotel_name,
        total_price_eur=total_price_eur,
        status=BookingStatus.confirmed,
    )
    session.add(booking)
    await session.flush()
    return booking


async def nearest_faq_chunks(
    session: AsyncSession, embedding: list[float], k: int = 4
) -> list[tuple[FAQChunk, float]]:
    distance = FAQChunk.embedding.cosine_distance(embedding).label("distance")
    result = await session.execute(select(FAQChunk, distance).order_by(distance).limit(k))
    return [(row.FAQChunk, float(row.distance)) for row in result]
