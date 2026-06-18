"""Amadeus (free test tier) — OPTIONAL price enrichment for the Budget and
Booking agents. Every function returns None on missing keys or any error, so
callers always fall back to heuristics. Prices are normalized to INR via fx.
"""
from __future__ import annotations

import time
from datetime import date as Date
from typing import Any

from app.config import settings
from app.resilience.errors import ExternalFetchError
from app.resilience.http import fetch_json
from app.tools import fx

_TOKEN: dict[str, Any] = {"value": None, "exp": 0.0}

# Minimal static IATA map for common Indian cities (avoids an extra lookup call).
_CITY_IATA = {
    "bangalore": "BLR", "bengaluru": "BLR", "goa": "GOI", "mumbai": "BOM",
    "delhi": "DEL", "new delhi": "DEL", "chennai": "MAA",
    "hyderabad": "HYD", "kolkata": "CCU", "pune": "PNQ", "jaipur": "JAI",
    "kochi": "COK", "ahmedabad": "AMD",
}


def _enabled() -> bool:
    return bool(settings.amadeus_client_id and settings.amadeus_client_secret)


async def _token() -> str | None:
    if not _enabled():
        return None
    if _TOKEN["value"] and time.time() < float(_TOKEN["exp"]):
        return str(_TOKEN["value"])
    try:
        data = await fetch_json(
            f"{settings.amadeus_base_url}/v1/security/oauth2/token",
            method="POST",
            data={
                "grant_type": "client_credentials",
                "client_id": settings.amadeus_client_id,
                "client_secret": settings.amadeus_client_secret,
            },
            timeout_s=6,
        )
    except ExternalFetchError:
        return None
    _TOKEN["value"] = data.get("access_token")
    _TOKEN["exp"] = time.time() + float(data.get("expires_in", 1700)) - 60
    return str(_TOKEN["value"]) if _TOKEN["value"] else None


async def _iata(city: str) -> str | None:
    key = city.strip().lower()
    if key in _CITY_IATA:
        return _CITY_IATA[key]
    token = await _token()
    if not token:
        return None
    try:
        data = await fetch_json(
            f"{settings.amadeus_base_url}/v1/reference-data/locations",
            params={"keyword": city, "subType": "CITY", "page[limit]": 1},
            headers={"Authorization": f"Bearer {token}"},
        )
    except ExternalFetchError:
        return None
    items = (data or {}).get("data") or []
    return items[0].get("iataCode") if items else None


async def cheapest_flight_inr(
    origin: str, destination: str, depart: Date, adults: int
) -> float | None:
    token = await _token()
    if not token:
        return None
    o, d = await _iata(origin), await _iata(destination)
    if not o or not d:
        return None
    try:
        data = await fetch_json(
            f"{settings.amadeus_base_url}/v2/shopping/flight-offers",
            params={
                "originLocationCode": o,
                "destinationLocationCode": d,
                "departureDate": depart.isoformat(),
                "adults": adults,
                "currencyCode": "INR",
                "max": 5,
            },
            headers={"Authorization": f"Bearer {token}"},
            timeout_s=12,
        )
    except ExternalFetchError:
        return None
    offers = (data or {}).get("data") or []
    prices = []
    for off in offers:
        price = off.get("price", {})
        amount = price.get("grandTotal") or price.get("total")
        if amount:
            prices.append(await fx.to_inr(float(amount), price.get("currency", "INR")))
    return min(prices) if prices else None


async def median_hotel_nightly_inr(
    city: str, check_in: Date, check_out: Date, adults: int
) -> float | None:
    token = await _token()
    if not token:
        return None
    code = await _iata(city)
    if not code:
        return None
    try:
        hotels = await fetch_json(
            f"{settings.amadeus_base_url}/v1/reference-data/locations/hotels/by-city",
            params={"cityCode": code},
            headers={"Authorization": f"Bearer {token}"},
        )
        hotel_ids = [h["hotelId"] for h in (hotels or {}).get("data", [])[:8] if h.get("hotelId")]
        if not hotel_ids:
            return None
        offers = await fetch_json(
            f"{settings.amadeus_base_url}/v3/shopping/hotel-offers",
            params={
                "hotelIds": ",".join(hotel_ids),
                "checkInDate": check_in.isoformat(),
                "checkOutDate": check_out.isoformat(),
                "adults": adults,
                "currency": "INR",
                "bestRateOnly": "true",
            },
            headers={"Authorization": f"Bearer {token}"},
            timeout_s=12,
        )
    except ExternalFetchError:
        return None
    nights = max((check_out - check_in).days, 1)
    rates: list[float] = []
    for h in (offers or {}).get("data", []):
        offer = (h.get("offers") or [{}])[0]
        price = offer.get("price", {})
        total = price.get("total")
        if total:
            inr = await fx.to_inr(float(total), price.get("currency", "INR"))
            rates.append(inr / nights)
    if not rates:
        return None
    rates.sort()
    return rates[len(rates) // 2]
