"""Shared helpers for agent nodes."""
from __future__ import annotations

from time import perf_counter

from app.schemas.trip import AgentRun


def record(agent: str, t0: float, status: str = "ok", detail: str | None = None) -> AgentRun:
    return AgentRun(
        agent=agent,
        status=status,
        latency_ms=round((perf_counter() - t0) * 1000, 2),
        detail=detail,
    )
