"""Planner agent — autonomous task decomposition of the natural-language query."""
from __future__ import annotations

from time import perf_counter

from app.graph.nodes._util import record
from app.graph.state import GraphState
from app.services.llm import decompose_query


async def planner_node(state: GraphState) -> dict:
    t0 = perf_counter()
    req, plan = await decompose_query(state.raw_query, state.preferences)
    return {
        "trip_request": req,
        "task_plan": plan,
        "agent_runs": [
            record("planner", t0, detail=f"{req.origin}->{req.destination}, {req.days}d")
        ],
    }
