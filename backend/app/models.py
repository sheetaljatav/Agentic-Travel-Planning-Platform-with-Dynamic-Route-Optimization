"""SQLAlchemy ORM models: trips, itineraries, agent_runs, preferences."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

# Use JSONB on Postgres, plain JSON elsewhere (e.g. SQLite in tests).
JsonType = JSON().with_variant(JSONB(), "postgresql")


def _uuid() -> str:
    return str(uuid.uuid4())


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    user_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    raw_query: Mapped[str] = mapped_column(String(1024))
    origin: Mapped[str] = mapped_column(String(120))
    destination: Mapped[str] = mapped_column(String(120))
    days: Mapped[int] = mapped_column(Integer)
    budget_cap: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    status: Mapped[str] = mapped_column(String(32), default="completed")

    itinerary: Mapped[Itinerary] = relationship(
        back_populates="trip", uselist=False, cascade="all, delete-orphan"
    )
    agent_runs: Mapped[list[AgentRunRow]] = relationship(
        back_populates="trip", cascade="all, delete-orphan"
    )


class Itinerary(Base):
    __tablename__ = "itineraries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    trip_id: Mapped[str] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"))
    total_cost: Mapped[float] = mapped_column(Float)
    within_budget: Mapped[bool] = mapped_column(default=True)
    data: Mapped[dict] = mapped_column(JsonType)  # full ItineraryOut payload

    trip: Mapped[Trip] = relationship(back_populates="itinerary")


class AgentRunRow(Base):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    trip_id: Mapped[str] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"))
    agent: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16))
    latency_ms: Mapped[float] = mapped_column(Float)
    detail: Mapped[str | None] = mapped_column(String(512), nullable=True)

    trip: Mapped[Trip] = relationship(back_populates="agent_runs")


class Preference(Base):
    __tablename__ = "preferences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    key: Mapped[str] = mapped_column(String(64))
    value: Mapped[str] = mapped_column(String(255))
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
