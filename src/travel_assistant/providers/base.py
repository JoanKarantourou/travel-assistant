from datetime import date, datetime
from decimal import Decimal
from typing import Protocol

from pydantic import BaseModel


class PriceInfo(BaseModel):
    currency: str
    total: Decimal


class FlightSegment(BaseModel):
    departure_iata: str
    arrival_iata: str
    departure_at: datetime
    arrival_at: datetime
    carrier_code: str
    flight_number: str
    duration_minutes: int


class FlightItinerary(BaseModel):
    segments: list[FlightSegment]
    total_duration_minutes: int


class FlightOffer(BaseModel):
    id: str
    price: PriceInfo
    itineraries: list[FlightItinerary]
    seats_remaining: int
    cabin_class: str = "ECONOMY"


class HotelInfo(BaseModel):
    name: str
    rating: int  # 1-5 stars
    city_code: str


class HotelOffer(BaseModel):
    id: str
    hotel: HotelInfo
    check_in: date
    check_out: date
    adults: int
    nightly_rate_eur: Decimal
    total_eur: Decimal
    room_type: str = "STANDARD"


class FlightProvider(Protocol):
    async def search_flights(
        self,
        origin: str,
        destination: str,
        depart_date: date,
        return_date: date | None,
        adults: int,
    ) -> list[FlightOffer]: ...


class HotelProvider(Protocol):
    async def search_hotels(
        self,
        city_code: str,
        check_in: date,
        check_out: date,
        adults: int,
    ) -> list[HotelOffer]: ...
