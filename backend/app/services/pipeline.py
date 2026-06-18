"""Orchestration: run the compiled agent graph, persist, update memory.

The compiled graph is stateless (full state is passed per invocation, no
checkpointer) so it is cached and reused across requests.
"""
from __future__ import annotations

from functools import lru_cache
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.graph.build import build_graph
from app.graph.state import GraphState
from app.schemas.trip import ItineraryOut
from app.services import memory, store

_RECURSION_LIMIT = 25


@lru_cache
def _graph():
    return build_graph()


async def generate_itinerary(
    session: AsyncSession, query: str, user_id: str | None
) -> ItineraryOut:
    trip_id = str(uuid4())
    preferences = await memory.get_preferences(session, user_id)

    init = GraphState(
        raw_query=query, trip_id=trip_id, user_id=user_id, preferences=preferences
    )
    final = await _graph().ainvoke(init, config={"recursion_limit": _RECURSION_LIMIT})

    itinerary: dict = final["itinerary"]
    await store.save_itinerary(session, itinerary, user_id)
    await memory.record_trip_signals(
        session, user_id, final["trip_request"], final["places"]
    )
    await session.commit()
    return ItineraryOut(**itinerary)
