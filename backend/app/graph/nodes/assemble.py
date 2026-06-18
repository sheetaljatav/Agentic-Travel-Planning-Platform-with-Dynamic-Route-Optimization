"""Assemble node — compile the final itinerary payload from all agent outputs."""
from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter

from app.graph.nodes._util import record
from app.graph.state import GraphState
from app.schemas.trip import ItineraryOut


async def assemble_node(state: GraphState) -> dict:
    t0 = perf_counter()
    req = state.trip_request
    assert req is not None and state.budget is not None

    # Attach each day's forecast to its itinerary day.
    days = list(state.day_plan)
    for i, day in enumerate(days):
        if i < len(state.weather):
            day.weather = state.weather[i]

    within = state.budget.within_cap
    summary = (
        f"{req.days}-day {req.destination} itinerary from {req.origin} for "
        f"{req.travelers} traveler(s): {len(state.places)} attractions over "
        f"{req.days} days, estimated {req.currency} {int(state.budget.total):,} "
        f"({'within' if within else 'over'} the {req.currency} {int(req.budget_cap):,} budget)."
    )

    runs = list(state.agent_runs) + [record("assemble", t0)]
    itinerary = ItineraryOut(
        trip_id=state.trip_id,
        request=req,
        days=days,
        budget=state.budget,
        bookings=state.bookings,
        weather=state.weather,
        total_cost=state.budget.total,
        within_budget=within,
        summary=summary,
        agent_runs=runs,
        created_at=datetime.now(timezone.utc),
    )
    return {"itinerary": itinerary.model_dump(mode="json")}
