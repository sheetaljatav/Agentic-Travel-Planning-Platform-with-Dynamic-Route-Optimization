"""Free OpenStreetMap / Nominatim geocoder (no API key; 1 req/s policy)."""
from __future__ import annotations

from app.config import settings
from app.providers.maps.base import GeocodeResult
from app.resilience.http import fetch_json
from app.schemas.trip import LatLng

_BASE = "https://nominatim.openstreetmap.org/search"


class NominatimGeocoder:
    name = "nominatim"

    async def geocode(self, query: str) -> GeocodeResult | None:
        rows = await fetch_json(
            _BASE,
            params={"q": query, "format": "jsonv2", "limit": 1, "addressdetails": 1},
            headers={"User-Agent": settings.nominatim_user_agent},
        )
        if not rows:
            return None
        top = rows[0]
        return GeocodeResult(
            name=top.get("display_name", query),
            location=LatLng(lat=float(top["lat"]), lng=float(top["lon"])),
            country=(top.get("address") or {}).get("country"),
        )
