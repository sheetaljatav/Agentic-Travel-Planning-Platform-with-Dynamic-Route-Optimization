"""Latency benchmark: parallel vs. sequential agent execution.

Measures the SAME nodes wired two ways (places∥weather vs. places→weather) so the
delta is purely the concurrency win — no artificial sleeps in the sequential path.

  python -m app.bench.latency            # offline, deterministic stub latencies
  python -m app.bench.latency --live     # hit the real free APIs (Nominatim/OSM,
                                         # Open-Meteo, Wikipedia) — no keys needed

Reports p50 over N runs for each topology and the measured improvement.
"""
from __future__ import annotations

import argparse
import asyncio
import statistics
from contextlib import ExitStack
from time import perf_counter
from unittest.mock import patch

from app.graph.build import build_graph
from app.graph.state import GraphState
from app.schemas.trip import LatLng, Place, WeatherDay

EXAMPLE_QUERY = "Plan a 4-day Goa trip under ₹25,000 from Bangalore"

# Representative real-world API latencies (seconds) used in offline mode.
_T_GEOCODE = 0.30
_T_POIS = 1.30
_T_WX_GEOCODE = 0.30
_T_WX_FORECAST = 0.60

_GOA = LatLng(lat=15.4, lng=73.9)
_STUB_PLACES = [
    Place(name=f"Goa Attraction {i}", location=LatLng(lat=15.3 + i * 0.03, lng=73.8 + i * 0.02),
          rating=7 - (i % 3), source="stub")
    for i in range(8)
]
_STUB_WX = [WeatherDay(summary="Partly cloudy", temp_max_c=31, temp_min_c=25) for _ in range(4)]


class _StubProvider:
    name = "stub"

    async def geocode(self, query: str):
        await asyncio.sleep(_T_GEOCODE)
        from app.providers.maps.base import GeocodeResult

        return GeocodeResult(name=query, location=_GOA)

    async def distance_matrix(self, points, *, profile="driving"):
        from app.providers.maps.base import haversine_matrix

        return haversine_matrix(points)

    async def directions(self, ordered, names, *, profile="driving"):
        from app.providers.maps.base import straight_line_legs

        return straight_line_legs(ordered, names)


async def _stub_find_pois(*args, **kwargs):
    await asyncio.sleep(_T_POIS)
    return list(_STUB_PLACES)


async def _stub_wx_geocode(*args, **kwargs):
    await asyncio.sleep(_T_WX_GEOCODE)
    return _GOA


async def _stub_forecast(*args, **kwargs):
    await asyncio.sleep(_T_WX_FORECAST)
    return list(_STUB_WX)


def _offline_patches() -> ExitStack:
    stack = ExitStack()
    stub = _StubProvider()
    stack.enter_context(patch("app.graph.nodes.places.get_maps_provider", lambda: stub))
    stack.enter_context(patch("app.graph.nodes.routing.get_maps_provider", lambda: stub))
    stack.enter_context(patch("app.graph.nodes.places.opentripmap.find_pois", _stub_find_pois))
    stack.enter_context(patch("app.graph.nodes.places.open_meteo.geocode", _stub_wx_geocode))
    stack.enter_context(patch("app.graph.nodes.weather.open_meteo.geocode", _stub_wx_geocode))
    stack.enter_context(patch("app.graph.nodes.weather.open_meteo.forecast", _stub_forecast))
    return stack


async def _timed_run(graph) -> float:
    init = GraphState(raw_query=EXAMPLE_QUERY, trip_id="bench")
    t0 = perf_counter()
    await graph.ainvoke(init, config={"recursion_limit": 25})
    return (perf_counter() - t0) * 1000


async def _measure(sequential: bool, runs: int) -> float:
    graph = build_graph(sequential=sequential)
    await _timed_run(graph)  # warmup
    samples = [await _timed_run(graph) for _ in range(runs)]
    return statistics.median(samples)


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=8)
    ap.add_argument("--live", action="store_true", help="hit real free APIs")
    args = ap.parse_args()

    with ExitStack() as stack:
        if not args.live:
            stack.enter_context(_offline_patches())
        seq = await _measure(sequential=True, runs=args.runs)
        par = await _measure(sequential=False, runs=args.runs)

    improvement = (seq - par) / seq * 100 if seq else 0.0
    mode = "LIVE (free APIs)" if args.live else "offline (stub latencies)"
    print(f"\nLatency benchmark - {mode}, p50 over {args.runs} runs")
    print(f"  sequential (places -> weather): {seq:8.0f} ms")
    print(f"  parallel   (places || weather): {par:8.0f} ms")
    print(f"  improvement:                    {improvement:7.1f}%\n")


if __name__ == "__main__":
    asyncio.run(main())
