"""Default maps provider: Nominatim geocode + OpenRouteService routing.

When ORS_API_KEY is absent, routing degrades to the haversine fallback so the
platform still produces an optimized, distance-aware itinerary with zero keys.
POI discovery is intentionally NOT here (it lives in tools/opentripmap.py).
"""
from __future__ import annotations

from app.config import settings
from app.providers.maps.base import (
    GeocodeResult,
    Matrix,
    haversine_matrix,
    straight_line_legs,
)
from app.providers.maps.nominatim import NominatimGeocoder
from app.resilience.errors import ExternalFetchError
from app.resilience.http import fetch_json
from app.schemas.trip import LatLng, Place, RouteLeg

_PROFILE = {"driving": "driving-car", "walking": "foot-walking", "cycling": "cycling-regular"}
_MATRIX_URL = "https://api.openrouteservice.org/v2/matrix/{profile}"
_DIRECTIONS_URL = "https://api.openrouteservice.org/v2/directions/{profile}"


class OpenRouteServiceProvider:
    name = "openrouteservice"

    def __init__(self) -> None:
        self._geocoder = NominatimGeocoder()
        self._key = settings.ors_api_key

    async def geocode(self, query: str) -> GeocodeResult | None:
        return await self._geocoder.geocode(query)

    async def distance_matrix(
        self, points: list[LatLng], *, profile: str = "driving"
    ) -> Matrix:
        if not self._key or len(points) < 2:
            return haversine_matrix(points)
        url = _MATRIX_URL.format(profile=_PROFILE.get(profile, "driving-car"))
        body = {
            "locations": [[p.lng, p.lat] for p in points],
            "metrics": ["distance", "duration"],
        }
        try:
            data = await fetch_json(
                url, method="POST", json=body, headers={"Authorization": self._key}
            )
            return Matrix(
                distances_m=data["distances"],
                durations_s=data["durations"],
                order=list(points),
            )
        except (ExternalFetchError, KeyError, TypeError):
            return haversine_matrix(points)

    async def directions(
        self, ordered: list[LatLng], names: list[str], *, profile: str = "driving"
    ) -> list[RouteLeg]:
        if not self._key or len(ordered) < 2:
            return straight_line_legs(ordered, names)
        url = _DIRECTIONS_URL.format(profile=_PROFILE.get(profile, "driving-car"))
        body = {"coordinates": [[p.lng, p.lat] for p in ordered]}
        try:
            data = await fetch_json(
                url, method="POST", json=body, headers={"Authorization": self._key}
            )
            segments = data["routes"][0]["segments"]
            legs: list[RouteLeg] = []
            for i, seg in enumerate(segments):
                legs.append(
                    RouteLeg(
                        from_idx=i,
                        to_idx=i + 1,
                        from_name=names[i],
                        to_name=names[i + 1],
                        distance_m=float(seg["distance"]),
                        duration_s=float(seg["duration"]),
                    )
                )
            return legs
        except (ExternalFetchError, KeyError, IndexError, TypeError):
            return straight_line_legs(ordered, names)

    async def places(
        self, near: LatLng, *, categories: list[str], limit: int
    ) -> list[Place]:
        raise NotImplementedError("ORS has no POI search; use tools/opentripmap.py")
