import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import delete

from tests.conftest import skip_no_db
from travel_assistant.persistence.database import get_session
from travel_assistant.persistence.models import Booking, BookingStatus
from travel_assistant.persistence.repositories import (
    create_booking,
    find_booking_by_customer_and_dates,
)


@skip_no_db
async def test_create_booking_persists_all_five_required_fields():
    customer_name = f"Alice Traveller {uuid.uuid4().hex[:8]}"
    booking = None
    try:
        async with get_session() as session:
            booking = await create_booking(
                session,
                customer_name=customer_name,
                start_date=date(2025, 9, 10),
                end_date=date(2025, 9, 17),
                destination="Rome",
                flight_number="AZ204",
                hotel_name="Hotel Colosseum",
                total_price_eur=Decimal("1450.00"),
            )

        assert booking.id is not None
        assert booking.customer_name == customer_name
        assert booking.destination == "Rome"
        assert booking.flight_number == "AZ204"
        assert booking.hotel_name == "Hotel Colosseum"
        assert booking.total_price_eur == Decimal("1450.00")
        assert booking.status == BookingStatus.confirmed
    finally:
        if booking and booking.id:
            async with get_session() as session:
                await session.execute(delete(Booking).where(Booking.id == booking.id))
                await session.commit()


@skip_no_db
async def test_booking_is_retrievable_by_customer_and_date():
    customer_name = f"Bob Explorer {uuid.uuid4().hex[:8]}"
    booking_id = None
    try:
        async with get_session() as session:
            created = await create_booking(
                session,
                customer_name=customer_name,
                start_date=date(2025, 10, 1),
                end_date=date(2025, 10, 8),
                destination="Tokyo",
                flight_number="JL407",
                hotel_name="Shinjuku Grand Hotel",
                total_price_eur=Decimal("2300.00"),
            )
        booking_id = created.id

        async with get_session() as session:
            found = await find_booking_by_customer_and_dates(session, customer_name, date(2025, 10, 1))

        assert found is not None
        assert str(found.id) == str(created.id)
        assert found.destination == "Tokyo"
        assert found.flight_number == "JL407"
        assert found.hotel_name == "Shinjuku Grand Hotel"
    finally:
        if booking_id:
            async with get_session() as session:
                await session.execute(delete(Booking).where(Booking.id == booking_id))
                await session.commit()


@skip_no_db
async def test_find_booking_returns_none_for_unknown_customer():
    async with get_session() as session:
        result = await find_booking_by_customer_and_dates(
            session, "No One At All", date(1999, 1, 1)
        )
    assert result is None
