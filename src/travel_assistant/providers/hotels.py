from travel_assistant.providers.base import HotelProvider
from travel_assistant.providers.mock_amadeus import MockAmadeusProvider

_provider: HotelProvider | None = None


def get_hotel_provider() -> HotelProvider:
    global _provider
    if _provider is None:
        _provider = MockAmadeusProvider()
    return _provider
