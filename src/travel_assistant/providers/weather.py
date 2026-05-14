"""Weather forecast retrieval via the Open-Meteo API.

Fetches daily temperature and precipitation data for a given coordinate range
without requiring an API key.
"""

from datetime import date

from pydantic import BaseModel

from travel_assistant.providers import get_http_client

_OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


class DailyForecast(BaseModel):
    """Weather summary for a single day at a location."""

    date: date
    temp_max: float
    temp_min: float
    precipitation_mm: float
    weather_code: int


class WeatherForecast(BaseModel):
    """Multi-day weather forecast for a specific coordinate."""

    latitude: float
    longitude: float
    daily: list[DailyForecast]


async def get_forecast(
    latitude: float,
    longitude: float,
    start_date: date,
    end_date: date,
) -> WeatherForecast:
    """Fetch a daily weather forecast from Open-Meteo for the given coordinates and date range."""
    response = await get_http_client().get(
        _OPEN_METEO_URL,
        params={
            "latitude": latitude,
            "longitude": longitude,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "timezone": "UTC",
        },
    )
    response.raise_for_status()
    data = response.json()

    daily_raw = data["daily"]
    days = [
        DailyForecast(
            date=date.fromisoformat(dt),
            temp_max=daily_raw["temperature_2m_max"][i],
            temp_min=daily_raw["temperature_2m_min"][i],
            precipitation_mm=daily_raw["precipitation_sum"][i],
            weather_code=daily_raw["weather_code"][i],
        )
        for i, dt in enumerate(daily_raw["time"])
    ]

    return WeatherForecast(latitude=data["latitude"], longitude=data["longitude"], daily=days)
