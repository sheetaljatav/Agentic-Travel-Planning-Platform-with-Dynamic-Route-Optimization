"""Currency conversion via a free no-key FX API, used to normalize non-INR
prices (e.g. Amadeus USD fares) into the trip currency."""
from __future__ import annotations

from app.config import settings
from app.resilience.errors import ExternalFetchError
from app.resilience.http import fetch_json

# Conservative static fallbacks (per 1 unit -> INR) used if the FX API is down.
_FALLBACK_TO_INR = {"USD": 83.0, "EUR": 90.0, "GBP": 105.0, "INR": 1.0}


async def to_inr(amount: float, currency: str) -> float:
    currency = (currency or "INR").upper()
    if currency == "INR":
        return amount
    try:
        data = await fetch_json(f"{settings.fx_base_url}/{currency}", timeout_s=4)
        rate = (data or {}).get("rates", {}).get("INR")
        if rate:
            return amount * float(rate)
    except ExternalFetchError:
        pass
    return amount * _FALLBACK_TO_INR.get(currency, 1.0)
