"""Wikipedia geosearch — free, no key. Used as the POI fallback when OpenTripMap
has no key, and to enrich place descriptions."""
from __future__ import annotations

from app.resilience.errors import ExternalFetchError
from app.resilience.http import fetch_json
from app.schemas.trip import LatLng, Place

_API = "https://en.wikipedia.org/w/api.php"

# Administrative / transport pages that are geotagged but aren't attractions.
_NOISE = (
    "railway station", "assembly constituency", "lok sabha", "district",
    "taluka", "tehsil", "municipal", "panchayat", "bus stand", "block",
    "subdivision", "ward", "pin code", "post office",
)


def _is_attraction(title: str) -> bool:
    low = title.lower()
    return not any(n in low for n in _NOISE)


async def geosearch(center: LatLng, *, radius_m: int = 15000, limit: int = 15) -> list[Place]:
    try:
        data = await fetch_json(
            _API,
            params={
                "action": "query",
                "list": "geosearch",
                "gscoord": f"{center.lat}|{center.lng}",
                "gsradius": min(radius_m, 10000),
                "gslimit": min(limit * 4, 100),
                "format": "json",
            },
        )
    except ExternalFetchError:
        return []
    items = (data or {}).get("query", {}).get("geosearch", [])
    places = [
        Place(
            name=it["title"],
            location=LatLng(lat=it["lat"], lng=it["lon"]),
            category="attraction",
            source="wikipedia",
        )
        for it in items
        if _is_attraction(it["title"])
    ]
    return places[:limit]


async def summary(title: str) -> str | None:
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
    try:
        data = await fetch_json(url)
    except ExternalFetchError:
        return None
    return (data or {}).get("extract")
