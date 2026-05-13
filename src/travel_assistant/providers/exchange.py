import time
from decimal import Decimal

from pydantic import BaseModel

from travel_assistant.providers import get_http_client

# Frankfurter is ECB-sourced, free, no API key required.
_FRANKFURTER_URL = "https://api.frankfurter.dev/v1/latest"
_CACHE_TTL = 600  # seconds

_rate_cache: dict[tuple[str, str], tuple[Decimal, float]] = {}


class ExchangeResult(BaseModel):
    from_ccy: str
    to_ccy: str
    amount: Decimal
    converted: Decimal
    rate: Decimal


async def convert(amount: Decimal, from_ccy: str, to_ccy: str) -> ExchangeResult:
    from_ccy = from_ccy.upper()
    to_ccy = to_ccy.upper()

    if from_ccy == to_ccy:
        return ExchangeResult(
            from_ccy=from_ccy,
            to_ccy=to_ccy,
            amount=amount,
            converted=amount,
            rate=Decimal("1"),
        )

    cache_key = (from_ccy, to_ccy)
    cached = _rate_cache.get(cache_key)
    now = time.monotonic()

    if cached and (now - cached[1]) < _CACHE_TTL:
        rate = cached[0]
    else:
        response = await get_http_client().get(
            _FRANKFURTER_URL, params={"from": from_ccy, "to": to_ccy}
        )
        response.raise_for_status()
        data = response.json()
        rate = Decimal(str(data["rates"][to_ccy]))
        _rate_cache[cache_key] = (rate, now)

    return ExchangeResult(
        from_ccy=from_ccy,
        to_ccy=to_ccy,
        amount=amount,
        converted=(amount * rate).quantize(Decimal("0.01")),
        rate=rate,
    )
