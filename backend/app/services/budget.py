"""Transparent line-item budget model for an India-domestic trip.

Each line prefers live data (Amadeus flights/hotels, normalized to INR) and falls
back to a documented heuristic, recording the source per line. Local-transport
cost is derived from the optimized route distance, which is what couples the
Routing and Budget agents and drives the bounded trim loop.
"""
from __future__ import annotations

import math
from datetime import date as Date
from datetime import timedelta

from app.schemas.trip import (
    BudgetBreakdown,
    BudgetLevel,
    Place,
    RouteLeg,
    TransportMode,
    TripRequest,
)
from app.tools import amadeus

PER_DIEM_FOOD = {BudgetLevel.budget: 600, BudgetLevel.mid: 1200, BudgetLevel.premium: 2500}
LODGING_TIER = {BudgetLevel.budget: 1500, BudgetLevel.mid: 3500, BudgetLevel.premium: 8000}
INTERCITY_ONEWAY_PP = {
    TransportMode.air: 4500,
    TransportMode.rail: 1200,
    TransportMode.road: 1500,
}
LOCAL_RATE_PER_KM = 15.0
LOCAL_DAILY_BASE = 150.0
ATTRACTION_DAILY_ALLOWANCE = 500.0
BUFFER_PCT = 0.10


def _route_km(legs: list[RouteLeg]) -> float:
    return sum(leg.distance_m for leg in legs) / 1000.0


async def _intercity(req: TripRequest) -> tuple[float, str]:
    if req.transport_mode == TransportMode.air:
        depart = req.start_date or Date.today()
        live = await amadeus.cheapest_flight_inr(
            req.origin, req.destination, depart, req.travelers
        )
        if live:
            return live * 2, "live"  # round trip (total already covers all travelers)
    oneway = INTERCITY_ONEWAY_PP[req.transport_mode]
    return oneway * 2 * req.travelers, "heuristic"


async def _lodging(req: TripRequest) -> tuple[float, str]:
    nights = max(req.days - 1, 1)
    rooms = math.ceil(req.travelers / 2)
    check_in = req.start_date or Date.today()
    check_out = check_in + timedelta(days=nights)
    live = await amadeus.median_hotel_nightly_inr(
        req.destination, check_in, check_out, req.travelers
    )
    if live:
        return live * nights * rooms, "live"
    return LODGING_TIER[req.budget_level] * nights * rooms, "heuristic"


async def estimate_budget(
    req: TripRequest, route_legs: list[RouteLeg], places: list[Place]
) -> BudgetBreakdown:
    intercity, s_intercity = await _intercity(req)
    lodging, s_lodging = await _lodging(req)

    local = _route_km(route_legs) * LOCAL_RATE_PER_KM + req.days * LOCAL_DAILY_BASE
    fees = sum(p.fee or 0 for p in places)
    attractions = fees if fees else ATTRACTION_DAILY_ALLOWANCE * req.days
    food = PER_DIEM_FOOD[req.budget_level] * req.days * req.travelers

    subtotal = intercity + lodging + local + attractions + food
    buffer = round(subtotal * BUFFER_PCT, 2)
    total = round(subtotal + buffer, 2)

    return BudgetBreakdown(
        intercity_transport=round(intercity, 2),
        lodging=round(lodging, 2),
        local_transport=round(local, 2),
        attractions=round(attractions, 2),
        food=round(food, 2),
        buffer=buffer,
        total=total,
        currency=req.currency,
        within_cap=total <= req.budget_cap,
        sources={
            "intercity_transport": s_intercity,
            "lodging": s_lodging,
            "local_transport": "derived",
            "attractions": "live" if fees else "heuristic",
            "food": "heuristic",
        },
    )
