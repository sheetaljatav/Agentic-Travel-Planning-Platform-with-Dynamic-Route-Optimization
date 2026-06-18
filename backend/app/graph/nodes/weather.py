"""Weather agent — daily forecast for the trip window.

Runs concurrently with the Places agent (independent geocode + API), which is
the primary source of the parallel-execution latency win.
"""
from __future__ import annotations

from time import perf_counter

from app.graph.nodes._util import record
from app.graph.state import GraphState
from app.tools import open_meteo


async def weather_node(state: GraphState) -> dict:
    t0 = perf_counter()
    req = state.trip_request
    assert req is not None

    center = await open_meteo.geocode(req.destination)
    if center is None:
        return {
            "weather": [],
            "agent_runs": [record("weather", t0, status="error", detail="geocode failed")],
        }
    days = await open_meteo.forecast(center, req.start_date, req.days)
    return {
        "weather": days,
        "agent_runs": [record("weather", t0, detail=f"{len(days)}-day forecast")],
    }
