"""Flight provider factory.

Returns the singleton ``FlightProvider`` in use by the application.
Swap ``MockAmadeusProvider`` for a real adapter here when one is available.
"""

from travel_assistant.providers.base import FlightProvider
from travel_assistant.providers.mock_amadeus import MockAmadeusProvider

_provider: FlightProvider | None = None


def get_flight_provider() -> FlightProvider:
    """Return the singleton ``FlightProvider``, creating it on first call."""
    global _provider
    if _provider is None:
        _provider = MockAmadeusProvider()
    return _provider
