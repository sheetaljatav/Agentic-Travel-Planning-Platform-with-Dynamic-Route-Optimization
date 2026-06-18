"""REST Countries — currency code / locale for a country (free, no key)."""
from __future__ import annotations

from app.resilience.errors import ExternalFetchError
from app.resilience.http import fetch_json

_BASE = "https://restcountries.com/v3.1/name/{name}"


async def currency_code(country: str) -> str | None:
    try:
        data = await fetch_json(
            _BASE.format(name=country), params={"fields": "currencies"}
        )
    except ExternalFetchError:
        return None
    if not data:
        return None
    currencies = (data[0] or {}).get("currencies") or {}
    return next(iter(currencies.keys()), None)
