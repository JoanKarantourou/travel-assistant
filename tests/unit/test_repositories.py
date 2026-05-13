import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from travel_assistant.persistence.models import BookingStatus, MessageRole
from travel_assistant.persistence.repositories import (
    append_message,
    create_booking,
    create_chat_session,
    find_booking_by_customer_and_dates,
    load_messages,
)


def _session() -> AsyncMock:
    s = AsyncMock()
    s.add = MagicMock()
    s.flush = AsyncMock()
    return s


def _execute_result(scalar=None, scalars_list=None):
    result = MagicMock()
    if scalars_list is not None:
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = scalars_list
        result.scalars.return_value = scalars_mock
    result.scalar_one_or_none.return_value = scalar
    return result


async def test_create_chat_session_adds_and_flushes():
    session = _session()
    chat = await create_chat_session(session, customer_name="Alice")
    session.add.assert_called_once()
    session.flush.assert_called_once()
    assert chat.customer_name == "Alice"


async def test_create_chat_session_without_name():
    session = _session()
    chat = await create_chat_session(session)
    assert chat.customer_name is None


async def test_append_message_returns_correct_fields():
    session = _session()
    sid = uuid.uuid4()
    msg = await append_message(session, sid, MessageRole.user, "Hello")
    session.add.assert_called_once()
    session.flush.assert_called_once()
    assert msg.content == "Hello"
    assert msg.role == MessageRole.user
    assert msg.session_id == sid
    assert msg.tool_name is None


async def test_append_message_with_tool_name():
    session = _session()
    sid = uuid.uuid4()
    msg = await append_message(
        session, sid, MessageRole.tool, '{"data": 1}', tool_name="get_weather"
    )
    assert msg.tool_name == "get_weather"


async def test_load_messages_returns_ordered_list():
    session = AsyncMock()
    m1, m2 = MagicMock(), MagicMock()
    session.execute = AsyncMock(return_value=_execute_result(scalars_list=[m1, m2]))
    messages = await load_messages(session, uuid.uuid4())
    assert messages == [m1, m2]


async def test_load_messages_empty_session():
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalars_list=[]))
    messages = await load_messages(session, uuid.uuid4())
    assert messages == []


async def test_find_booking_returns_none_when_missing():
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=None))
    result = await find_booking_by_customer_and_dates(session, "Ghost", date(2025, 1, 1))
    assert result is None


async def test_find_booking_returns_booking_when_found():
    session = AsyncMock()
    booking_mock = MagicMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=booking_mock))
    result = await find_booking_by_customer_and_dates(session, "Alice", date(2025, 7, 1))
    assert result is booking_mock


async def test_create_booking_sets_all_five_required_fields():
    session = _session()
    booking = await create_booking(
        session,
        customer_name="Bob",
        start_date=date(2025, 8, 1),
        end_date=date(2025, 8, 10),
        destination="Paris",
        flight_number="BA304",
        hotel_name="Hotel du Louvre",
        total_price_eur=Decimal("1200.00"),
    )
    session.add.assert_called_once()
    session.flush.assert_called_once()
    assert booking.customer_name == "Bob"
    assert booking.destination == "Paris"
    assert booking.flight_number == "BA304"
    assert booking.hotel_name == "Hotel du Louvre"
    assert booking.total_price_eur == Decimal("1200.00")
    assert booking.status == BookingStatus.confirmed


async def test_create_booking_status_defaults_to_confirmed():
    session = _session()
    booking = await create_booking(
        session,
        customer_name="Carol",
        start_date=date(2025, 9, 1),
        end_date=date(2025, 9, 5),
        destination="Madrid",
        flight_number="IB3456",
        hotel_name="Palacio Hotel",
        total_price_eur=Decimal("850.50"),
    )
    assert booking.status == BookingStatus.confirmed
