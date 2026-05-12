import json
from datetime import date
from decimal import Decimal

from langchain_core.tools import tool

from travel_assistant.observability.tracing import track_tool_call
from travel_assistant.persistence.database import get_session
from travel_assistant.persistence.repositories import (
    create_booking as _db_create_booking,
)
from travel_assistant.persistence.repositories import (
    find_booking_by_customer_and_dates,
)
from travel_assistant.providers.exchange import convert
from travel_assistant.providers.flights import get_flight_provider
from travel_assistant.providers.hotels import get_hotel_provider
from travel_assistant.providers.weather import get_forecast
from travel_assistant.rag.retriever import search_faqs


@tool
@track_tool_call("get_weather")
async def get_weather(latitude: float, longitude: float, start_date: str, end_date: str) -> str:
    """Get daily weather forecast for a location.

    Args:
        latitude: Decimal latitude of the destination.
        longitude: Decimal longitude of the destination.
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.
    """
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    forecast = await get_forecast(latitude, longitude, start, end)
    days = [
        {
            "date": d.date.isoformat(),
            "temp_max_c": d.temp_max,
            "temp_min_c": d.temp_min,
            "precipitation_mm": d.precipitation_mm,
            "weather_code": d.weather_code,
        }
        for d in forecast.daily
    ]
    return json.dumps(days)


@tool
@track_tool_call("convert_currency")
async def convert_currency(amount: float, from_ccy: str, to_ccy: str) -> str:
    """Convert an amount from one currency to another.

    Args:
        amount: Amount to convert.
        from_ccy: Source ISO 4217 currency code (e.g., USD).
        to_ccy: Target ISO 4217 currency code (e.g., EUR).
    """
    result = await convert(Decimal(str(amount)), from_ccy.upper(), to_ccy.upper())
    return json.dumps(
        {
            "original": float(result.amount),
            "converted": float(result.converted),
            "rate": float(result.rate),
            "from": result.from_ccy,
            "to": result.to_ccy,
        }
    )


@tool
@track_tool_call("search_flights")
async def search_flights(
    origin: str,
    destination: str,
    depart_date: str,
    return_date: str | None,
    adults: int,
) -> str:
    """Search available flights.

    Args:
        origin: Departure IATA airport code (e.g., ATH).
        destination: Arrival IATA airport code (e.g., LHR).
        depart_date: Departure date in YYYY-MM-DD format.
        return_date: Return date in YYYY-MM-DD format, or null for one-way.
        adults: Number of adult passengers.
    """
    provider = get_flight_provider()
    depart = date.fromisoformat(depart_date)
    ret = date.fromisoformat(return_date) if return_date else None
    offers = await provider.search_flights(origin.upper(), destination.upper(), depart, ret, adults)
    data = []
    for o in offers:
        segments = []
        for itin in o.itineraries:
            for seg in itin.segments:
                segments.append(
                    {
                        "flight_number": seg.flight_number,
                        "from": seg.departure_iata,
                        "to": seg.arrival_iata,
                        "departs": seg.departure_at.isoformat(),
                        "arrives": seg.arrival_at.isoformat(),
                        "duration_minutes": seg.duration_minutes,
                    }
                )
        data.append(
            {
                "id": o.id,
                "price_eur": float(o.price.total),
                "cabin": o.cabin_class,
                "seats_remaining": o.seats_remaining,
                "segments": segments,
            }
        )
    return json.dumps(data)


@tool
@track_tool_call("search_hotels")
async def search_hotels(city_code: str, check_in: str, check_out: str, adults: int) -> str:
    """Search available hotels in a city.

    Args:
        city_code: IATA city code (e.g., ATH, LHR).
        check_in: Check-in date in YYYY-MM-DD format.
        check_out: Check-out date in YYYY-MM-DD format.
        adults: Number of adult guests.
    """
    provider = get_hotel_provider()
    ci = date.fromisoformat(check_in)
    co = date.fromisoformat(check_out)
    offers = await provider.search_hotels(city_code.upper(), ci, co, adults)
    data = [
        {
            "id": o.id,
            "hotel_name": o.hotel.name,
            "rating": o.hotel.rating,
            "room_type": o.room_type,
            "nightly_rate_eur": float(o.nightly_rate_eur),
            "total_eur": float(o.total_eur),
            "check_in": o.check_in.isoformat(),
            "check_out": o.check_out.isoformat(),
        }
        for o in offers
    ]
    return json.dumps(data)


@tool
@track_tool_call("lookup_faq")
async def lookup_faq(query: str) -> str:
    """Search the FAQ knowledge base for answers to common questions.

    Args:
        query: Natural language question to search for.
    """
    results = await search_faqs(query, k=4)
    data = [
        {"content": r.content, "source": r.source, "page": r.page, "score": r.score}
        for r in results
    ]
    return json.dumps(data)


@tool
@track_tool_call("find_existing_booking")
async def find_existing_booking(customer_name: str, start_date: str) -> str:
    """Look up an existing booking by customer name and start date.

    Args:
        customer_name: Full name of the customer.
        start_date: Trip start date in YYYY-MM-DD format.
    """
    sd = date.fromisoformat(start_date)
    async with get_session() as session:
        booking = await find_booking_by_customer_and_dates(session, customer_name, sd)
    if booking is None:
        return json.dumps({"found": False})
    return json.dumps(
        {
            "found": True,
            "booking_id": str(booking.id),
            "destination": booking.destination,
            "flight_number": booking.flight_number,
            "hotel_name": booking.hotel_name,
            "start_date": booking.start_date.isoformat(),
            "end_date": booking.end_date.isoformat(),
            "total_price_eur": float(booking.total_price_eur),
            "status": str(booking.status),
        }
    )


@tool
@track_tool_call("create_booking")
async def create_booking(
    customer_name: str,
    start_date: str,
    end_date: str,
    destination: str,
    flight_number: str,
    hotel_name: str,
    total_price_eur: float,
) -> str:
    """Create a booking after the customer has confirmed all details.

    Args:
        customer_name: Full name of the customer.
        start_date: Trip start date in YYYY-MM-DD format.
        end_date: Trip end date in YYYY-MM-DD format.
        destination: Destination city or country.
        flight_number: Flight number from search results.
        hotel_name: Hotel name from search results.
        total_price_eur: Total trip price in EUR (flights + hotel combined).
    """
    sd = date.fromisoformat(start_date)
    ed = date.fromisoformat(end_date)
    async with get_session() as session:
        booking = await _db_create_booking(
            session,
            customer_name=customer_name,
            start_date=sd,
            end_date=ed,
            destination=destination,
            flight_number=flight_number,
            hotel_name=hotel_name,
            total_price_eur=Decimal(str(total_price_eur)),
        )
    return json.dumps(
        {
            "booking_id": str(booking.id),
            "status": str(booking.status),
            "customer_name": booking.customer_name,
            "destination": booking.destination,
            "flight_number": booking.flight_number,
            "hotel_name": booking.hotel_name,
            "start_date": booking.start_date.isoformat(),
            "end_date": booking.end_date.isoformat(),
            "total_price_eur": float(booking.total_price_eur),
        }
    )


@tool
@track_tool_call("escalate_to_human")
async def escalate_to_human(reason: str) -> str:
    """Hand the conversation off to a human agent.

    Args:
        reason: Brief description of why escalation is needed.
    """
    return json.dumps({"escalated": True, "reason": reason})


all_tools = [
    get_weather,
    convert_currency,
    search_flights,
    search_hotels,
    lookup_faq,
    find_existing_booking,
    create_booking,
    escalate_to_human,
]
