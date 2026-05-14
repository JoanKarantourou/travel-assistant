"""Data-access functions (repository pattern) for all ORM models.

Each function accepts an open ``AsyncSession`` and performs a single
database operation, keeping transaction control with the caller.
"""

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
    """Insert a new ``ChatSession`` row and return it with its generated ID."""
    chat_session = ChatSession(customer_name=customer_name)
    session.add(chat_session)
    await session.flush()
    return chat_session


async def get_chat_session(session: AsyncSession, session_id: uuid.UUID) -> ChatSession | None:
    """Return the ``ChatSession`` for the given ID, or ``None`` if not found."""
    result = await session.execute(select(ChatSession).where(ChatSession.id == session_id))
    return result.scalar_one_or_none()


async def append_message(
    session: AsyncSession,
    session_id: uuid.UUID,
    role: MessageRole,
    content: str,
    tool_name: str | None = None,
) -> ChatMessage:
    """Append a ``ChatMessage`` to the given session and return it with its generated ID."""
    msg = ChatMessage(session_id=session_id, role=role, content=content, tool_name=tool_name)
    session.add(msg)
    await session.flush()
    return msg


async def load_messages(session: AsyncSession, session_id: uuid.UUID) -> list[ChatMessage]:
    """Return all messages for a session, ordered by creation time."""
    result = await session.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    return list(result.scalars().all())


async def find_booking_by_customer_and_dates(
    session: AsyncSession, customer_name: str, start_date: date
) -> Booking | None:
    """Look up a booking by customer name and trip start date, or return ``None``."""
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
    """Insert a new confirmed ``Booking`` row and return it with its generated ID."""
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
    """Return the *k* FAQ chunks closest to *embedding* by cosine distance, with their scores."""
    # cosine_distance returns a pgvector expression that is used both in the
    # ORDER BY clause and projected as a named column so each row carries its
    # distance alongside the ORM object.
    distance = FAQChunk.embedding.cosine_distance(embedding).label("distance")
    result = await session.execute(select(FAQChunk, distance).order_by(distance).limit(k))
    return [(row.FAQChunk, float(row.distance)) for row in result]
