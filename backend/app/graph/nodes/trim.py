"""Trim node — autonomous re-planning when over budget.

Applies the highest-leverage cuts first (switch intercity air->rail, drop one
budget tier, remove the lowest-rated stop), then re-enters routing so distances
and cost are recomputed. Bounded to one pass by the budget router's trim_count.
"""
from __future__ import annotations

from time import perf_counter

from app.graph.nodes._util import record
from app.graph.state import GraphState
from app.schemas.trip import BudgetLevel, TransportMode

_DOWNGRADE = {
    BudgetLevel.premium: BudgetLevel.mid,
    BudgetLevel.mid: BudgetLevel.budget,
    BudgetLevel.budget: BudgetLevel.budget,
}


async def trim_node(state: GraphState) -> dict:
    t0 = perf_counter()
    req = state.trip_request
    assert req is not None

    actions: list[str] = []
    update: dict = {}
    if req.transport_mode == TransportMode.air:
        update["transport_mode"] = TransportMode.rail
        actions.append("air->rail")
    new_level = _DOWNGRADE[req.budget_level]
    if new_level != req.budget_level:
        update["budget_level"] = new_level
        actions.append(f"tier->{new_level.value}")

    places = list(state.places)
    if len(places) > 3:
        places.sort(key=lambda p: (p.rating or 0))
        dropped = places.pop(0)
        actions.append(f"dropped {dropped.name}")

    new_req = req.model_copy(update=update) if update else req
    return {
        "trip_request": new_req,
        "places": places,
        "trim_count": state.trim_count + 1,
        "agent_runs": [record("trim", t0, detail=", ".join(actions) or "no-op")],
    }
