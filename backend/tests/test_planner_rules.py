import pytest

from app.schemas.trip import TransportMode
from app.services.llm import decompose_query


@pytest.mark.asyncio
async def test_parses_goa_example():
    req, plan = await decompose_query(
        "Plan a 4-day Goa trip under ₹25,000 from Bangalore"
    )
    assert req.destination == "Goa"
    assert req.origin == "Bangalore"
    assert req.days == 4
    assert req.budget_cap == 25000
    assert req.currency == "INR"
    assert len(plan) == 5  # five decomposed tasks


@pytest.mark.asyncio
async def test_parses_train_and_interests():
    req, _ = await decompose_query(
        "5 day beach and history trip to Goa from Mumbai by train, budget 30k"
    )
    assert req.transport_mode == TransportMode.rail
    assert req.budget_cap == 30000
    assert "beach" in req.interests and "history" in req.interests
