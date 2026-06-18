"""StateGraph wiring for the 5-agent pipeline.

Parallel topology (default):
    planner -> {places, weather} -> routing -> budget -> (trim? -> routing) -> booking -> assemble

`sequential=True` forces weather before places (one extra edge) and is used ONLY
by the latency benchmark to measure the parallel-execution speedup on the same
nodes — no sleeps, a real apples-to-apples comparison.
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.graph.nodes.assemble import assemble_node
from app.graph.nodes.booking import booking_node
from app.graph.nodes.budget import budget_node
from app.graph.nodes.places import places_node
from app.graph.nodes.planner import planner_node
from app.graph.nodes.routing import routing_node
from app.graph.nodes.trim import trim_node
from app.graph.nodes.weather import weather_node
from app.graph.state import GraphState

MAX_TRIM = 1


def budget_router(state: GraphState) -> str:
    if state.over_budget and state.trim_count < MAX_TRIM:
        return "trim"
    return "ok"


def build_graph(*, sequential: bool = False, checkpointer=None):
    g = StateGraph(GraphState)
    g.add_node("planner", planner_node)
    g.add_node("places", places_node)
    g.add_node("weather", weather_node)
    g.add_node("routing", routing_node)
    g.add_node("budget", budget_node)
    g.add_node("trim", trim_node)
    g.add_node("booking", booking_node)
    g.add_node("assemble", assemble_node)

    g.add_edge(START, "planner")
    if sequential:
        g.add_edge("planner", "weather")
        g.add_edge("weather", "places")
        g.add_edge("places", "routing")
    else:
        # fan-out: both edges fire in the same super-step (parallel execution)
        g.add_edge("planner", "places")
        g.add_edge("planner", "weather")
        # fan-in: routing barrier-joins both branches automatically
        g.add_edge("places", "routing")
        g.add_edge("weather", "routing")

    g.add_edge("routing", "budget")
    g.add_conditional_edges("budget", budget_router, {"trim": "trim", "ok": "booking"})
    g.add_edge("trim", "routing")
    g.add_edge("booking", "assemble")
    g.add_edge("assemble", END)

    return g.compile(checkpointer=checkpointer)
