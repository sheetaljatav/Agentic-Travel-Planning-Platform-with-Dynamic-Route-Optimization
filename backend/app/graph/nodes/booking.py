"""Booking agent — non-transactional booking suggestions (links only).

Never executes a transaction; surfaces actionable deep links and the budgeted
price so the user can complete bookings themselves.
"""
from __future__ import annotations

from datetime import date as Date
from time import perf_counter
from urllib.parse import quote_plus

from app.graph.nodes._util import record
from app.graph.state import GraphState
from app.schemas.trip import BookingSuggestion, TransportMode

_TRANSPORT = {
    TransportMode.air: ("Google Flights", "https://www.google.com/travel/flights?q=flights%20from%20{o}%20to%20{d}"),
    TransportMode.rail: ("IRCTC", "https://www.irctc.co.in/nget/train-search"),
    TransportMode.road: ("Self-drive / cabs", "https://www.google.com/maps/dir/{o}/{d}"),
}


async def booking_node(state: GraphState) -> dict:
    t0 = perf_counter()
    req = state.trip_request
    assert req is not None
    bd = state.budget
    check_in = (req.start_date or Date.today()).isoformat()

    suggestions: list[BookingSuggestion] = []

    provider, url_tpl = _TRANSPORT[req.transport_mode]
    suggestions.append(
        BookingSuggestion(
            type="transport",
            title=f"{req.transport_mode.value.title()} · {req.origin} → {req.destination}",
            provider=provider,
            url=url_tpl.format(o=quote_plus(req.origin), d=quote_plus(req.destination)),
            price=bd.intercity_transport if bd else None,
            currency=req.currency,
            note="Round trip estimate" if bd else None,
        )
    )
    suggestions.append(
        BookingSuggestion(
            type="hotel",
            title=f"Stay in {req.destination} ({req.budget_level.value} tier)",
            provider="Booking.com",
            url=(
                "https://www.booking.com/searchresults.html?"
                f"ss={quote_plus(req.destination)}&checkin={check_in}"
                f"&group_adults={req.travelers}"
            ),
            price=bd.lodging if bd else None,
            currency=req.currency,
            note=f"{max(req.days - 1, 1)} night(s)",
        )
    )
    if state.places:
        top = state.places[0]
        suggestions.append(
            BookingSuggestion(
                type="attraction",
                title=f"Plan a visit: {top.name}",
                provider="Local operators",
                url=f"https://www.google.com/search?q={quote_plus(top.name + ' tickets')}",
                note="Top-rated attraction on the optimized route",
            )
        )

    return {
        "bookings": suggestions,
        "agent_runs": [record("booking", t0, detail=f"{len(suggestions)} suggestions")],
    }
