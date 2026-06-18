"""Shared graph state.

Reducer note: only `agent_runs` and `errors` use the `add` reducer because BOTH
parallel branches (places, weather) append to them in the same super-step.
`places` and `weather` are distinct keys written by one node each, so they must
NOT be annotated — doing so would corrupt the fan-out merge.
"""
from __future__ import annotations

from operator import add
from typing import Annotated

from pydantic import BaseModel, Field

from app.schemas.trip import (
    AgentRun,
    BookingSuggestion,
    BudgetBreakdown,
    ItineraryDay,
    Place,
    RouteLeg,
    TripRequest,
    WeatherDay,
)


class GraphState(BaseModel):
    # inputs (seeded by the API layer)
    raw_query: str
    trip_id: str
    user_id: str | None = None
    preferences: list[dict] = Field(default_factory=list)

    # planner output
    trip_request: TripRequest | None = None
    task_plan: list[str] = Field(default_factory=list)

    # parallel branch outputs (distinct keys -> no reducer)
    places: list[Place] = Field(default_factory=list)
    weather: list[WeatherDay] = Field(default_factory=list)

    # downstream
    route: list[RouteLeg] = Field(default_factory=list)
    day_plan: list[ItineraryDay] = Field(default_factory=list)
    budget: BudgetBreakdown | None = None
    bookings: list[BookingSuggestion] = Field(default_factory=list)
    itinerary: dict | None = None  # final ItineraryOut payload

    # control
    over_budget: bool = False
    trim_count: int = 0

    # observability (written by many nodes -> reducer required)
    agent_runs: Annotated[list[AgentRun], add] = Field(default_factory=list)
    errors: Annotated[list[str], add] = Field(default_factory=list)
