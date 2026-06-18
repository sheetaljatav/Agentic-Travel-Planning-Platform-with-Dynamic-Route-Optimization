"""OpenTripMap POI discovery with a bounded-concurrency detail fan-out.

Mirrors the legacy attractions.ts pattern: radius search -> concurrent detail
lookups (Semaphore-bounded) -> drop failures. Falls back to Wikipedia geosearch
when no OPENTRIPMAP_API_KEY is configured.
"""
from __future__ import annotations

import asyncio

from app.config import settings
from app.resilience.errors import ExternalFetchError
from app.resilience.http import fetch_json
from app.schemas.trip import LatLng, Place
from app.tools import wikipedia

_RADIUS = "https://api.opentripmap.com/0.1/en/places/radius"
_XID = "https://api.opentripmap.com/0.1/en/places/xid/{xid}"

# interest keyword -> OpenTripMap "kinds"
_KIND_MAP = {
    "beach": "beaches",
    "beaches": "beaches",
    "history": "historic,architecture",
    "historic": "historic,architecture",
    "heritage": "historic,architecture",
    "culture": "cultural,museums",
    "museum": "museums",
    "art": "museums,cultural",
    "nature": "natural",
    "wildlife": "natural",
    "food": "foods",
    "temple": "religion",
    "religion": "religion",
    "nightlife": "amusements",
    "adventure": "sport,natural",
}
_DEFAULT_KINDS = "interesting_places,beaches,cultural,historic,natural,architecture"


def kinds_for_interests(interests: list[str]) -> str:
    if not interests:
        return _DEFAULT_KINDS
    kinds: list[str] = []
    for it in interests:
        mapped = _KIND_MAP.get(it.strip().lower())
        if mapped:
            kinds.extend(mapped.split(","))
    return ",".join(dict.fromkeys(kinds)) or _DEFAULT_KINDS


async def _detail(xid: str, sem: asyncio.Semaphore) -> Place | None:
    async with sem:
        try:
            d = await fetch_json(
                _XID.format(xid=xid), params={"apikey": settings.opentripmap_api_key}
            )
        except ExternalFetchError:
            return None
    point = d.get("point") or {}
    if "lat" not in point or "lon" not in point:
        return None
    kinds = (d.get("kinds") or "").split(",")
    return Place(
        name=d.get("name") or "Attraction",
        location=LatLng(lat=point["lat"], lng=point["lon"]),
        category=kinds[0] if kinds and kinds[0] else "attraction",
        xid=xid,
        rating=float(d["rate"]) if str(d.get("rate", "")).isdigit() else None,
        description=(d.get("wikipedia_extracts") or {}).get("text"),
        source="opentripmap",
    )


async def find_pois(
    center: LatLng, *, interests: list[str], limit: int = 12, radius_m: int = 20000
) -> list[Place]:
    """Return up to `limit` named POIs near `center`, biased by interests."""
    if not settings.opentripmap_api_key:
        return await wikipedia.geosearch(center, radius_m=radius_m, limit=limit)

    try:
        features = await fetch_json(
            _RADIUS,
            params={
                "radius": radius_m,
                "lon": center.lng,
                "lat": center.lat,
                "kinds": kinds_for_interests(interests),
                "rate": 2,  # only rated/notable places
                "format": "json",
                "limit": limit * 2,
                "apikey": settings.opentripmap_api_key,
            },
        )
    except ExternalFetchError:
        return await wikipedia.geosearch(center, radius_m=radius_m, limit=limit)

    xids = [f["xid"] for f in (features or []) if f.get("name") and f.get("xid")]
    if not xids:
        return await wikipedia.geosearch(center, radius_m=radius_m, limit=limit)

    sem = asyncio.Semaphore(3)
    results = await asyncio.gather(*(_detail(x, sem) for x in xids[: limit * 2]))
    places = [p for p in results if p is not None]
    # de-dupe by name, keep highest-rated first
    places.sort(key=lambda p: (p.rating or 0), reverse=True)
    seen: set[str] = set()
    unique: list[Place] = []
    for p in places:
        if p.name in seen:
            continue
        seen.add(p.name)
        unique.append(p)
    return unique[:limit]
