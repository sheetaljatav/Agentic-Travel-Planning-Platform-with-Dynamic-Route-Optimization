"""Routing agent — dynamic route optimization.

Builds a travel-time matrix from the maps provider, orders the stops with the
local 2-opt optimizer (no paid key required), fetches leg directions, and splits
the optimized sequence across days. Re-runs after a trim, recomputing distances.
"""
from __future__ import annotations

import math
from time import perf_counter

from app.graph.nodes._util import record
from app.graph.state import GraphState
from app.providers.maps.factory import get_maps_provider
from app.schemas.trip import ItineraryDay, Place, RouteLeg
from app.services.optimize import optimize_order


def _split_days(ordered: list[Place], legs: list[RouteLeg], days: int) -> list[ItineraryDay]:
    days = max(days, 1)
    if not ordered:
        return [ItineraryDay(day=d + 1) for d in range(days)]
    per_day = math.ceil(len(ordered) / days)
    out: list[ItineraryDay] = []
    idx = 0
    for d in range(days):
        chunk = ordered[idx : idx + per_day]
        travel_s = sum(
            legs[k].duration_s
            for k in range(idx, idx + len(chunk) - 1)
            if k < len(legs)
        )
        out.append(
            ItineraryDay(day=d + 1, stops=chunk, travel_time_min=round(travel_s / 60, 1))
        )
        idx += per_day
    return out


async def routing_node(state: GraphState) -> dict:
    t0 = perf_counter()
    req = state.trip_request
    assert req is not None
    places = state.places

    if len(places) < 2:
        return {
            "route": [],
            "day_plan": _split_days(places, [], req.days),
            "agent_runs": [record("routing", t0, detail=f"{len(places)} stop(s), no optimization")],
        }

    maps = get_maps_provider()
    matrix = await maps.distance_matrix([p.location for p in places])
    order = optimize_order(matrix.durations_s, start=0)
    ordered = [places[i] for i in order]
    names = [p.name for p in ordered]
    legs = await maps.directions([p.location for p in ordered], names)

    total_km = round(sum(leg.distance_m for leg in legs) / 1000, 1)
    return {
        "route": legs,
        "day_plan": _split_days(ordered, legs, req.days),
        # keep state.places in optimized order so trim/budget see the same sequence
        "places": ordered,
        "agent_runs": [record("routing", t0, detail=f"{len(ordered)} stops, {total_km} km")],
    }
