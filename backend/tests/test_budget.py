import pytest

from app.schemas.trip import (
    BudgetLevel,
    LatLng,
    Place,
    RouteLeg,
    TransportMode,
    TripRequest,
)
from app.services.budget import estimate_budget


@pytest.mark.asyncio
async def test_heuristic_lines_and_cap():
    req = TripRequest(
        raw_query="x",
        origin="Bangalore",
        destination="Goa",
        days=4,
        travelers=2,
        budget_cap=25000,
        budget_level=BudgetLevel.budget,
        transport_mode=TransportMode.rail,
    )
    legs = [
        RouteLeg(from_idx=0, to_idx=1, from_name="a", to_name="b",
                 distance_m=20000, duration_s=2400)
    ]
    places = [Place(name="a", location=LatLng(lat=15, lng=73))]

    bd = await estimate_budget(req, legs, places)

    assert bd.currency == "INR"
    assert bd.intercity_transport == 1200 * 2 * 2  # rail round trip, both travelers
    assert bd.lodging == 1500 * 3  # budget tier x 3 nights x 1 room
    assert bd.sources["intercity_transport"] == "heuristic"
    assert bd.within_cap is (bd.total <= req.budget_cap)
    assert bd.total == pytest.approx(18700, abs=1)
