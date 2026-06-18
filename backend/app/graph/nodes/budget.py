"""Budget agent — line-item cost estimate vs the user's cap."""
from __future__ import annotations

from time import perf_counter

from app.graph.nodes._util import record
from app.graph.state import GraphState
from app.services.budget import estimate_budget


async def budget_node(state: GraphState) -> dict:
    t0 = perf_counter()
    req = state.trip_request
    assert req is not None
    bd = await estimate_budget(req, state.route, state.places)
    detail = f"{bd.currency} {int(bd.total):,} vs cap {int(req.budget_cap):,}"
    return {
        "budget": bd,
        "over_budget": not bd.within_cap,
        "agent_runs": [record("budget", t0, detail=detail)],
    }
