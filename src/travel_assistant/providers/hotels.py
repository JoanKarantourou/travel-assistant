"""Hotel provider factory.

Returns the singleton ``HotelProvider`` in use by the application.
Swap ``MockAmadeusProvider`` for a real adapter here when one is available.
"""

from travel_assistant.providers.base import HotelProvider
from travel_assistant.providers.mock_amadeus import MockAmadeusProvider

_provider: HotelProvider | None = None


def get_hotel_provider() -> HotelProvider:
    """Return the singleton ``HotelProvider``, creating it on first call."""
    global _provider
    if _provider is None:
        _provider = MockAmadeusProvider()
    return _provider
