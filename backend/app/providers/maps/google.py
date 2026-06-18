"""Google Maps provider (Geocoding / Distance Matrix / Directions / Places).

Used automatically when GOOGLE_MAPS_API_KEY is set. Mirrors the ORS provider's
neutral return types and degrades to haversine on any API error.
"""
from __future__ import annotations

from app.config import settings
from app.providers.maps.base import (
    GeocodeResult,
    Matrix,
    haversine_matrix,
    straight_line_legs,
)
from app.resilience.errors import ExternalFetchError
from app.resilience.http import fetch_json
from app.schemas.trip import LatLng, Place, RouteLeg

_GEOCODE = "https://maps.googleapis.com/maps/api/geocode/json"
_MATRIX = "https://maps.googleapis.com/maps/api/distancematrix/json"
_DIRECTIONS = "https://maps.googleapis.com/maps/api/directions/json"
_NEARBY = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"


class GoogleMapsProvider:
    name = "google"

    def __init__(self) -> None:
        self._key = settings.google_maps_api_key

    async def geocode(self, query: str) -> GeocodeResult | None:
        data = await fetch_json(_GEOCODE, params={"address": query, "key": self._key})
        results = (data or {}).get("results") or []
        if not results:
            return None
        top = results[0]
        loc = top["geometry"]["location"]
        country = next(
            (
                c["long_name"]
                for c in top.get("address_components", [])
                if "country" in c.get("types", [])
            ),
            None,
        )
        return GeocodeResult(
            name=top.get("formatted_address", query),
            location=LatLng(lat=loc["lat"], lng=loc["lng"]),
            country=country,
        )

    async def distance_matrix(
        self, points: list[LatLng], *, profile: str = "driving"
    ) -> Matrix:
        if len(points) < 2:
            return haversine_matrix(points)
        coords = "|".join(f"{p.lat},{p.lng}" for p in points)
        try:
            data = await fetch_json(
                _MATRIX,
                params={"origins": coords, "destinations": coords,
                        "mode": profile, "key": self._key},
            )
            rows = data["rows"]
            dist = [[e["distance"]["value"] for e in r["elements"]] for r in rows]
            dur = [[e["duration"]["value"] for e in r["elements"]] for r in rows]
            return Matrix(distances_m=dist, durations_s=dur, order=list(points))
        except (ExternalFetchError, KeyError, TypeError):
            return haversine_matrix(points)

    async def directions(
        self, ordered: list[LatLng], names: list[str], *, profile: str = "driving"
    ) -> list[RouteLeg]:
        if len(ordered) < 2:
            return straight_line_legs(ordered, names)
        params = {
            "origin": f"{ordered[0].lat},{ordered[0].lng}",
            "destination": f"{ordered[-1].lat},{ordered[-1].lng}",
            "mode": profile,
            "key": self._key,
        }
        if len(ordered) > 2:
            params["waypoints"] = "|".join(
                f"{p.lat},{p.lng}" for p in ordered[1:-1]
            )
        try:
            data = await fetch_json(_DIRECTIONS, params=params)
            g_legs = data["routes"][0]["legs"]
            legs: list[RouteLeg] = []
            for i, leg in enumerate(g_legs):
                legs.append(
                    RouteLeg(
                        from_idx=i,
                        to_idx=i + 1,
                        from_name=names[i],
                        to_name=names[i + 1],
                        distance_m=float(leg["distance"]["value"]),
                        duration_s=float(leg["duration"]["value"]),
                    )
                )
            return legs
        except (ExternalFetchError, KeyError, IndexError, TypeError):
            return straight_line_legs(ordered, names)

    async def places(
        self, near: LatLng, *, categories: list[str], limit: int
    ) -> list[Place]:
        data = await fetch_json(
            _NEARBY,
            params={
                "location": f"{near.lat},{near.lng}",
                "radius": 15000,
                "type": "tourist_attraction",
                "key": self._key,
            },
        )
        out: list[Place] = []
        for r in (data or {}).get("results", [])[:limit]:
            loc = r["geometry"]["location"]
            out.append(
                Place(
                    name=r.get("name", "Attraction"),
                    location=LatLng(lat=loc["lat"], lng=loc["lng"]),
                    category="attraction",
                    rating=r.get("rating"),
                    source="google_places",
                )
            )
        return out
