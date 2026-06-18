"""Places agent — discover and rank attractions near the destination.

Independent of the weather branch, so the two run concurrently. Internally fans
out POI-detail calls (bounded concurrency lives in tools/opentripmap.py).
"""
from __future__ import annotations

from time import perf_counter

from app.graph.nodes._util import record
from app.graph.state import GraphState
from app.providers.maps.factory import get_maps_provider
from app.schemas.trip import Place
from app.tools import open_meteo, opentripmap


def _target_count(days: int) -> int:
    return max(min(days * 2, 12), 4)


def _bias_by_preferences(places: list[Place], preferences: list[dict]) -> list[Place]:
    preferred = {p["value"] for p in preferences if p["key"] in ("category", "interest")}
    if not preferred:
        return places
    return sorted(
        places,
        key=lambda pl: (any(t in pl.category for t in preferred), pl.rating or 0),
        reverse=True,
    )


async def places_node(state: GraphState) -> dict:
    t0 = perf_counter()
    req = state.trip_request
    assert req is not None

    geo = await get_maps_provider().geocode(req.destination)
    center = geo.location if geo else await open_meteo.geocode(req.destination)
    if center is None:
        return {
            "places": [],
            "errors": [f"could not geocode {req.destination}"],
            "agent_runs": [record("places", t0, status="error", detail="geocode failed")],
        }

    pois = await opentripmap.find_pois(
        center, interests=req.interests, limit=_target_count(req.days), radius_m=30000
    )
    pois = _bias_by_preferences(pois, state.preferences)[: _target_count(req.days)]
    return {
        "places": pois,
        "agent_runs": [record("places", t0, detail=f"{len(pois)} attractions")],
    }
