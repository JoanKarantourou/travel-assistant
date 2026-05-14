"""Shared data models and provider protocols for flights and hotels.

Defines the Pydantic value objects used across providers and the structural
``Protocol`` types that concrete provider adapters must satisfy.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Protocol

from pydantic import BaseModel


class PriceInfo(BaseModel):
    """A monetary amount in a named currency."""

    currency: str
    total: Decimal


class FlightSegment(BaseModel):
    """A single non-stop leg of a flight itinerary."""

    departure_iata: str
    arrival_iata: str
    departure_at: datetime
    arrival_at: datetime
    carrier_code: str
    flight_number: str
    duration_minutes: int


class FlightItinerary(BaseModel):
    """An ordered collection of segments representing one direction of a journey."""

    segments: list[FlightSegment]
    total_duration_minutes: int


class FlightOffer(BaseModel):
    """A bookable flight offer returned by a ``FlightProvider``."""

    id: str
    price: PriceInfo
    itineraries: list[FlightItinerary]
    seats_remaining: int
    cabin_class: str = "ECONOMY"


class HotelInfo(BaseModel):
    """Basic descriptive information about a hotel property."""

    name: str
    rating: int  # 1-5 stars
    city_code: str


class HotelOffer(BaseModel):
    """A bookable hotel offer returned by a ``HotelProvider``."""

    id: str
    hotel: HotelInfo
    check_in: date
    check_out: date
    adults: int
    nightly_rate_eur: Decimal
    total_eur: Decimal
    room_type: str = "STANDARD"


class FlightProvider(Protocol):
    """Structural protocol that any flight-search adapter must satisfy."""

    async def search_flights(
        self,
        origin: str,
        destination: str,
        depart_date: date,
        return_date: date | None,
        adults: int,
    ) -> list[FlightOffer]: ...


class HotelProvider(Protocol):
    """Structural protocol that any hotel-search adapter must satisfy."""

    async def search_hotels(
        self,
        city_code: str,
        check_in: date,
        check_out: date,
        adults: int,
    ) -> list[HotelOffer]: ...
