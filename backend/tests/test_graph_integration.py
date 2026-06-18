import pytest

from app.graph.build import build_graph
from app.graph.state import GraphState


@pytest.mark.asyncio
async def test_full_pipeline_runs_all_agents_and_trims(stub_external):
    graph = build_graph()
    init = GraphState(
        raw_query="Plan a 4-day Goa trip under ₹25,000 from Bangalore", trip_id="t1"
    )
    final = await graph.ainvoke(init, config={"recursion_limit": 25})

    itin = final["itinerary"]
    assert itin is not None

    agents = {r["agent"] for r in itin["agent_runs"]}
    assert {"planner", "places", "weather", "routing", "budget", "booking", "assemble"} <= agents
    assert "trim" in agents  # Goa example exceeds the cap -> one autonomous trim pass

    assert len(itin["days"]) == 4
    assert itin["within_budget"] is True
    assert len(final["route"]) == len(final["places"]) - 1
    assert all(d["stops"] for d in itin["days"][:1])  # at least the first day has stops


@pytest.mark.asyncio
async def test_parallel_and_sequential_produce_equivalent_plans(stub_external):
    init = GraphState(raw_query="3-day Goa trip from Bangalore under 40000", trip_id="t2")
    par = await build_graph(sequential=False).ainvoke(init, config={"recursion_limit": 25})
    seq = await build_graph(sequential=True).ainvoke(init, config={"recursion_limit": 25})
    # topology differs but the resulting itinerary content matches
    assert par["itinerary"]["total_cost"] == seq["itinerary"]["total_cost"]
    assert len(par["itinerary"]["days"]) == len(seq["itinerary"]["days"]) == 3
