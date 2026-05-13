from datetime import date
from decimal import Decimal

import httpx
import pytest
import respx

from travel_assistant.providers.exchange import convert
from travel_assistant.providers.mock_amadeus import MockAmadeusProvider
from travel_assistant.providers.weather import get_forecast

_METEO_RESPONSE = {
    "latitude": 48.8566,
    "longitude": 2.3522,
    "daily": {
        "time": ["2025-07-01", "2025-07-02"],
        "temperature_2m_max": [25.1, 26.3],
        "temperature_2m_min": [15.2, 16.1],
        "precipitation_sum": [0.0, 2.5],
        "weather_code": [1, 2],
    },
}

_FRANKFURTER_RESPONSE = {
    "amount": 1.0,
    "base": "USD",
    "date": "2025-07-01",
    "rates": {"EUR": 0.89},
}


@respx.mock
async def test_get_forecast_parses_response():
    respx.get("https://api.open-meteo.com/v1/forecast").mock(
        return_value=httpx.Response(200, json=_METEO_RESPONSE)
    )
    forecast = await get_forecast(48.8566, 2.3522, date(2025, 7, 1), date(2025, 7, 2))
    assert len(forecast.daily) == 2
    assert forecast.daily[0].temp_max == pytest.approx(25.1)
    assert forecast.daily[1].precipitation_mm == pytest.approx(2.5)


@respx.mock
async def test_get_forecast_raises_on_error():
    respx.get("https://api.open-meteo.com/v1/forecast").mock(return_value=httpx.Response(503))
    with pytest.raises(httpx.HTTPStatusError):
        await get_forecast(0.0, 0.0, date(2025, 7, 1), date(2025, 7, 2))


@respx.mock
async def test_convert_currency():
    respx.get("https://api.frankfurter.app/latest").mock(
        return_value=httpx.Response(200, json=_FRANKFURTER_RESPONSE)
    )
    result = await convert(Decimal("100"), "USD", "EUR")
    assert result.converted == Decimal("89.00")
    assert result.rate == Decimal("0.89")
    assert result.from_ccy == "USD"
    assert result.to_ccy == "EUR"


async def test_convert_same_currency_no_request():
    result = await convert(Decimal("50"), "EUR", "EUR")
    assert result.converted == Decimal("50")
    assert result.rate == Decimal("1")


async def test_mock_amadeus_flight_determinism():
    provider = MockAmadeusProvider()
    offers_a = await provider.search_flights("LHR", "CDG", date(2025, 7, 1), None, 2)
    offers_b = await provider.search_flights("LHR", "CDG", date(2025, 7, 1), None, 2)
    assert len(offers_a) == len(offers_b)
    for a, b in zip(offers_a, offers_b, strict=True):
        assert a.id == b.id
        assert a.price.total == b.price.total
        seg_a = a.itineraries[0].segments[0].flight_number
        seg_b = b.itineraries[0].segments[0].flight_number
        assert seg_a == seg_b


async def test_mock_amadeus_hotel_determinism():
    provider = MockAmadeusProvider()
    offers_a = await provider.search_hotels("ATH", date(2025, 7, 1), date(2025, 7, 7), 2)
    offers_b = await provider.search_hotels("ATH", date(2025, 7, 1), date(2025, 7, 7), 2)
    assert len(offers_a) == len(offers_b)
    for a, b in zip(offers_a, offers_b, strict=True):
        assert a.id == b.id
        assert a.total_eur == b.total_eur


async def test_mock_amadeus_different_routes_differ():
    provider = MockAmadeusProvider()
    lhr_cdg = await provider.search_flights("LHR", "CDG", date(2025, 7, 1), None, 1)
    jfk_ath = await provider.search_flights("JFK", "ATH", date(2025, 7, 1), None, 1)
    assert {o.id for o in lhr_cdg}.isdisjoint({o.id for o in jfk_ath})


async def test_mock_amadeus_flight_count_in_range():
    provider = MockAmadeusProvider()
    offers = await provider.search_flights("FRA", "SIN", date(2025, 8, 15), None, 1)
    assert 3 <= len(offers) <= 5


async def test_mock_amadeus_hotel_count_in_range():
    provider = MockAmadeusProvider()
    offers = await provider.search_hotels("DXB", date(2025, 8, 1), date(2025, 8, 5), 2)
    assert 2 <= len(offers) <= 4


async def test_mock_amadeus_prices_are_eur():
    provider = MockAmadeusProvider()
    offers = await provider.search_flights("MAD", "FCO", date(2025, 9, 1), None, 1)
    for offer in offers:
        assert offer.price.currency == "EUR"
