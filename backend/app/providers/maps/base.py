"""Maps provider abstraction.

Routing never sees provider JSON: every provider returns these neutral types.
A haversine fallback makes geo/routing work with no API key at all.
"""
from __future__ import annotations

import math
from typing import Protocol

from pydantic import BaseModel

from app.schemas.trip import LatLng, Place, RouteLeg


class GeocodeResult(BaseModel):
    name: str
    location: LatLng
    country: str | None = None


class Matrix(BaseModel):
    """Square matrices in metres and seconds; row/col order == input order."""

    distances_m: list[list[float]]
    durations_s: list[list[float]]
    order: list[LatLng]


class MapsProvider(Protocol):
    name: str

    async def geocode(self, query: str) -> GeocodeResult | None: ...

    async def distance_matrix(
        self, points: list[LatLng], *, profile: str = "driving"
    ) -> Matrix: ...

    async def directions(
        self, ordered: list[LatLng], names: list[str], *, profile: str = "driving"
    ) -> list[RouteLeg]: ...

    async def places(
        self, near: LatLng, *, categories: list[str], limit: int
    ) -> list[Place]: ...


# --------------------------------------------------------------- haversine

_EARTH_RADIUS_M = 6_371_000.0
# Blended urban driving speed (km/h) used to derive durations when no routing API.
_FALLBACK_SPEED_KMH = 28.0


def haversine_m(a: LatLng, b: LatLng) -> float:
    p1, p2 = math.radians(a.lat), math.radians(b.lat)
    dphi = math.radians(b.lat - a.lat)
    dlmb = math.radians(b.lng - a.lng)
    h = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * _EARTH_RADIUS_M * math.asin(math.sqrt(h))


def haversine_matrix(points: list[LatLng]) -> Matrix:
    n = len(points)
    dist = [[0.0] * n for _ in range(n)]
    dur = [[0.0] * n for _ in range(n)]
    speed_ms = _FALLBACK_SPEED_KMH * 1000 / 3600
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            d = haversine_m(points[i], points[j])
            dist[i][j] = d
            dur[i][j] = d / speed_ms
    return Matrix(distances_m=dist, durations_s=dur, order=list(points))


def straight_line_legs(ordered: list[LatLng], names: list[str]) -> list[RouteLeg]:
    speed_ms = _FALLBACK_SPEED_KMH * 1000 / 3600
    legs: list[RouteLeg] = []
    for i in range(len(ordered) - 1):
        d = haversine_m(ordered[i], ordered[i + 1])
        legs.append(
            RouteLeg(
                from_idx=i,
                to_idx=i + 1,
                from_name=names[i],
                to_name=names[i + 1],
                distance_m=d,
                duration_s=d / speed_ms,
            )
        )
    return legs
