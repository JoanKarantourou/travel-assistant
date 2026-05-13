from datetime import date
from decimal import Decimal

import pytest

from tests.conftest import skip_no_db
from travel_assistant.persistence.database import get_session
from travel_assistant.persistence.models import BookingStatus
from travel_assistant.persistence.repositories import (
    create_booking,
    find_booking_by_customer_and_dates,
)


@skip_no_db
async def test_create_booking_persists_all_five_required_fields():
    async with get_session() as session:
        booking = await create_booking(
            session,
            customer_name="Alice Traveller",
            start_date=date(2025, 9, 10),
            end_date=date(2025, 9, 17),
            destination="Rome",
            flight_number="AZ204",
            hotel_name="Hotel Colosseum",
            total_price_eur=Decimal("1450.00"),
        )

    assert booking.id is not None
    assert booking.customer_name == "Alice Traveller"
    assert booking.destination == "Rome"
    assert booking.flight_number == "AZ204"
    assert booking.hotel_name == "Hotel Colosseum"
    assert booking.total_price_eur == Decimal("1450.00")
    assert booking.status == BookingStatus.confirmed


@skip_no_db
async def test_booking_is_retrievable_by_customer_and_date():
    async with get_session() as session:
        created = await create_booking(
            session,
            customer_name="Bob Explorer",
            start_date=date(2025, 10, 1),
            end_date=date(2025, 10, 8),
            destination="Tokyo",
            flight_number="JL407",
            hotel_name="Shinjuku Grand Hotel",
            total_price_eur=Decimal("2300.00"),
        )

    async with get_session() as session:
        found = await find_booking_by_customer_and_dates(
            session, "Bob Explorer", date(2025, 10, 1)
        )

    assert found is not None
    assert str(found.id) == str(created.id)
    assert found.destination == "Tokyo"
    assert found.flight_number == "JL407"
    assert found.hotel_name == "Shinjuku Grand Hotel"


@skip_no_db
async def test_find_booking_returns_none_for_unknown_customer():
    async with get_session() as session:
        result = await find_booking_by_customer_and_dates(
            session, "No One At All", date(1999, 1, 1)
        )
    assert result is None
