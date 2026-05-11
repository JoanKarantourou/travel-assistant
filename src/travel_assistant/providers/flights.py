from travel_assistant.providers.base import FlightProvider
from travel_assistant.providers.mock_amadeus import MockAmadeusProvider

_provider: FlightProvider | None = None


def get_flight_provider() -> FlightProvider:
    global _provider
    if _provider is None:
        _provider = MockAmadeusProvider()
    return _provider
