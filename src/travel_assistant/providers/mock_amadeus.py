"""
Mock implementation of FlightProvider and HotelProvider.

The Amadeus self-service API is scheduled for decommission in July 2026.
This mock mirrors the Amadeus REST response shape so the rest of the codebase
can exercise the provider protocols without an external dependency. To wire a
real adapter, implement FlightProvider or HotelProvider from base.py and swap
the factory in flights.py / hotels.py.

Outputs are deterministic: the same query inputs always produce the same offers,
but different inputs produce different results.
"""
import hashlib
import random
from datetime import date, datetime, timedelta
from decimal import Decimal

from travel_assistant.providers.base import (
    FlightItinerary,
    FlightOffer,
    FlightSegment,
    HotelInfo,
    HotelOffer,
    PriceInfo,
)

_IATA_CODES = ["LHR", "CDG", "JFK", "ATH", "AMS", "FRA", "MAD", "FCO", "DXB", "SIN", "BKK", "NRT"]
_CARRIERS = ["BA", "LH", "AA", "A3", "KL", "AF", "IB", "AZ", "EK", "SQ"]
_HOTELS = [
    "Grand Palace Hotel",
    "City Centre Suites",
    "Harbour View Hotel",
    "The Metropolitan",
    "Plaza Garden Inn",
    "Old Town Boutique",
    "Skyline Towers",
]
_ROOM_TYPES = ["STANDARD", "DELUXE", "SUITE"]


class MockAmadeusProvider:
    def _rng(self, *keys: str) -> random.Random:
        digest = hashlib.md5("|".join(keys).encode()).hexdigest()
        return random.Random(int(digest, 16) % (2**32))

    async def search_flights(
        self,
        origin: str,
        destination: str,
        depart_date: date,
        return_date: date | None,
        adults: int,
    ) -> list[FlightOffer]:
        rng = self._rng(origin, destination, str(depart_date))
        offers = []
        for i in range(rng.randint(3, 5)):
            carrier = rng.choice(_CARRIERS)
            flight_num = rng.randint(100, 999)
            dep_hour = rng.randint(6, 20)
            duration = rng.randint(60, 720)
            dep_dt = datetime(depart_date.year, depart_date.month, depart_date.day, dep_hour, 0)
            arr_dt = dep_dt + timedelta(minutes=duration)
            segment = FlightSegment(
                departure_iata=origin.upper(),
                arrival_iata=destination.upper(),
                departure_at=dep_dt,
                arrival_at=arr_dt,
                carrier_code=carrier,
                flight_number=f"{carrier}{flight_num}",
                duration_minutes=duration,
            )
            price = Decimal(str(round(rng.uniform(80, 1200), 2)))
            offers.append(
                FlightOffer(
                    id=f"mock-{origin}-{destination}-{depart_date}-{i}",
                    price=PriceInfo(currency="EUR", total=price),
                    itineraries=[
                        FlightItinerary(segments=[segment], total_duration_minutes=duration)
                    ],
                    seats_remaining=rng.randint(1, 9),
                )
            )
        return offers

    async def search_hotels(
        self,
        city_code: str,
        check_in: date,
        check_out: date,
        adults: int,
    ) -> list[HotelOffer]:
        rng = self._rng(city_code, str(check_in), str(check_out))
        nights = max((check_out - check_in).days, 1)
        offers = []
        for i in range(rng.randint(2, 4)):
            nightly = Decimal(str(round(rng.uniform(50, 400), 2)))
            offers.append(
                HotelOffer(
                    id=f"mock-{city_code}-{check_in}-{i}",
                    hotel=HotelInfo(
                        name=rng.choice(_HOTELS),
                        rating=rng.randint(3, 5),
                        city_code=city_code.upper(),
                    ),
                    check_in=check_in,
                    check_out=check_out,
                    adults=adults,
                    nightly_rate_eur=nightly,
                    total_eur=(nightly * nights).quantize(Decimal("0.01")),
                    room_type=rng.choice(_ROOM_TYPES),
                )
            )
        return offers
