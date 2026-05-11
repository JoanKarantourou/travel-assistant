"""Insert sample bookings for manual testing. Safe to run multiple times."""
import asyncio
from datetime import date
from decimal import Decimal

from travel_assistant.persistence.database import get_session
from travel_assistant.persistence.repositories import (
    create_booking,
    find_booking_by_customer_and_dates,
)

SAMPLES = [
    {
        "customer_name": "Alice Papadopoulos",
        "start_date": date(2026, 7, 10),
        "end_date": date(2026, 7, 17),
        "destination": "Athens",
        "flight_number": "A3 601",
        "hotel_name": "Hotel Grande Bretagne",
        "total_price_eur": Decimal("1250.00"),
    },
    {
        "customer_name": "Bob Müller",
        "start_date": date(2026, 8, 5),
        "end_date": date(2026, 8, 12),
        "destination": "Paris",
        "flight_number": "LH 1234",
        "hotel_name": "Hotel Le Marais",
        "total_price_eur": Decimal("1890.50"),
    },
    {
        "customer_name": "Carol Smith",
        "start_date": date(2026, 9, 20),
        "end_date": date(2026, 9, 27),
        "destination": "New York",
        "flight_number": "BA 177",
        "hotel_name": "The Manhattan Hotel",
        "total_price_eur": Decimal("2340.00"),
    },
]


async def main() -> None:
    async with get_session() as session:
        for data in SAMPLES:
            existing = await find_booking_by_customer_and_dates(
                session, data["customer_name"], data["start_date"]
            )
            if existing:
                print(f"skip (exists): {data['customer_name']} -> {data['destination']}")
            else:
                await create_booking(session, **data)
                print(f"seeded: {data['customer_name']} -> {data['destination']}")


if __name__ == "__main__":
    asyncio.run(main())
