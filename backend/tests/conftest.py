"""Test fixtures: in-process SQLite DB + stubbed external APIs (no network)."""
from __future__ import annotations

import os

# Must be set before any `app.*` import so the cached settings pick it up.
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
os.environ["ANTHROPIC_API_KEY"] = ""  # force deterministic rule-based planner

from contextlib import ExitStack  # noqa: E402
from unittest.mock import patch  # noqa: E402

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402

from app.providers.maps.base import GeocodeResult, haversine_matrix, straight_line_legs  # noqa: E402
from app.schemas.trip import LatLng, Place, WeatherDay  # noqa: E402

_GOA = LatLng(lat=15.4, lng=73.9)
STUB_PLACES = [
    Place(name=f"Goa Spot {i}", location=LatLng(lat=15.3 + i * 0.04, lng=73.8 + i * 0.03),
          rating=7 - (i % 4), category="beaches" if i % 2 else "historic", source="stub")
    for i in range(8)
]
STUB_WEATHER = [WeatherDay(summary="Partly cloudy", temp_max_c=31, temp_min_c=25) for _ in range(4)]


class StubProvider:
    name = "stub"

    async def geocode(self, query: str):
        return GeocodeResult(name=query, location=_GOA)

    async def distance_matrix(self, points, *, profile="driving"):
        return haversine_matrix(points)

    async def directions(self, ordered, names, *, profile="driving"):
        return straight_line_legs(ordered, names)


async def _stub_find_pois(*a, **k):
    return list(STUB_PLACES)


async def _stub_geocode(*a, **k):
    return _GOA


async def _stub_forecast(*a, **k):
    return list(STUB_WEATHER)


@pytest.fixture
def stub_external():
    """Patch the network-touching tools used by the places/weather agents."""
    with ExitStack() as stack:
        stub = StubProvider()
        stack.enter_context(patch("app.graph.nodes.places.get_maps_provider", lambda: stub))
        stack.enter_context(patch("app.graph.nodes.routing.get_maps_provider", lambda: stub))
        stack.enter_context(patch("app.graph.nodes.places.opentripmap.find_pois", _stub_find_pois))
        stack.enter_context(patch("app.graph.nodes.places.open_meteo.geocode", _stub_geocode))
        stack.enter_context(patch("app.graph.nodes.weather.open_meteo.geocode", _stub_geocode))
        stack.enter_context(patch("app.graph.nodes.weather.open_meteo.forecast", _stub_forecast))
        yield


@pytest_asyncio.fixture(autouse=True)
async def fresh_db():
    """Recreate tables before each test for isolation."""
    from app.db import Base, engine, init_db

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_db()
    yield
