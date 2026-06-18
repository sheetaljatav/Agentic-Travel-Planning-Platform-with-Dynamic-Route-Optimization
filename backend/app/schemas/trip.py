"""Pydantic models shared by agents, persistence (JSONB), and the API.

A single set of serializable types avoids dataclass<->pydantic conversion at the
provider boundary and lets itineraries round-trip straight into Postgres JSONB.
"""
from __future__ import annotations

from datetime import date as Date
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class TransportMode(str, Enum):
    air = "air"
    rail = "rail"
    road = "road"


class BudgetLevel(str, Enum):
    budget = "budget"
    mid = "mid"
    premium = "premium"


class LatLng(BaseModel):
    lat: float
    lng: float


# ---------------------------------------------------------------- request

class TripRequest(BaseModel):
    """Structured trip intent produced by the Planner agent."""

    raw_query: str
    origin: str = "Bangalore"
    destination: str = "Goa"
    days: int = Field(default=3, ge=1, le=21)
    start_date: Date | None = None
    travelers: int = Field(default=2, ge=1, le=20)
    budget_cap: float = Field(default=25000, ge=0)
    currency: str = "INR"
    budget_level: BudgetLevel = BudgetLevel.budget
    transport_mode: TransportMode = TransportMode.air
    interests: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------- domain

class Place(BaseModel):
    name: str
    location: LatLng
    category: str = "attraction"
    xid: str | None = None
    rating: float | None = None
    fee: float | None = None  # entry fee in trip currency, if known
    description: str | None = None
    source: str = "opentripmap"


class WeatherDay(BaseModel):
    date: Date | None = None
    summary: str
    temp_min_c: float | None = None
    temp_max_c: float | None = None
    precipitation_mm: float | None = None


class RouteLeg(BaseModel):
    from_idx: int
    to_idx: int
    from_name: str
    to_name: str
    distance_m: float
    duration_s: float
    polyline: str | None = None


class BudgetBreakdown(BaseModel):
    intercity_transport: float = 0
    lodging: float = 0
    local_transport: float = 0
    attractions: float = 0
    food: float = 0
    buffer: float = 0
    total: float = 0
    currency: str = "INR"
    within_cap: bool = True
    sources: dict[str, str] = Field(default_factory=dict)  # line -> live | heuristic


class BookingSuggestion(BaseModel):
    type: str  # hotel | transport | attraction
    title: str
    provider: str
    url: str | None = None
    price: float | None = None
    currency: str | None = None
    note: str | None = None


class ItineraryDay(BaseModel):
    day: int
    date: Date | None = None
    weather: WeatherDay | None = None
    stops: list[Place] = Field(default_factory=list)
    travel_time_min: float = 0


class AgentRun(BaseModel):
    agent: str
    status: str  # ok | error | skipped
    latency_ms: float
    detail: str | None = None


# ---------------------------------------------------------------- API I/O

class PlanRequestIn(BaseModel):
    query: str = Field(
        ..., examples=["Plan a 4-day Goa trip under ₹25,000 from Bangalore"]
    )
    user_id: str | None = None


class ItineraryOut(BaseModel):
    trip_id: str
    request: TripRequest
    days: list[ItineraryDay]
    budget: BudgetBreakdown
    bookings: list[BookingSuggestion]
    weather: list[WeatherDay] = Field(default_factory=list)
    total_cost: float
    within_budget: bool
    summary: str
    agent_runs: list[AgentRun] = Field(default_factory=list)
    created_at: datetime | None = None
