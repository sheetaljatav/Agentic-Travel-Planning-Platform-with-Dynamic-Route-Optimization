"""Persistence of completed trips/itineraries/agent-runs (no commit — the caller
owns the transaction so trip signals and itinerary save atomically)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AgentRunRow, Itinerary, Trip


async def save_itinerary(
    session: AsyncSession, itinerary: dict, user_id: str | None
) -> None:
    req = itinerary["request"]
    trip = Trip(
        id=itinerary["trip_id"],
        user_id=user_id,
        raw_query=req["raw_query"],
        origin=req["origin"],
        destination=req["destination"],
        days=req["days"],
        budget_cap=req["budget_cap"],
        currency=req["currency"],
        status="completed",
    )
    session.add(trip)
    session.add(
        Itinerary(
            trip_id=trip.id,
            total_cost=itinerary["total_cost"],
            within_budget=itinerary["within_budget"],
            data=itinerary,
        )
    )
    for run in itinerary["agent_runs"]:
        session.add(
            AgentRunRow(
                trip_id=trip.id,
                agent=run["agent"],
                status=run["status"],
                latency_ms=run["latency_ms"],
                detail=run.get("detail"),
            )
        )


async def get_itinerary(session: AsyncSession, trip_id: str) -> dict | None:
    row = (
        await session.execute(
            select(Itinerary).where(Itinerary.trip_id == trip_id)
        )
    ).scalar_one_or_none()
    return row.data if row else None
