"""Memory-aware recommendations: read prior preferences for the Planner, and
write back recency-weighted signals after each trip so the next trip personalizes.
"""
from __future__ import annotations

from collections import Counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Preference
from app.schemas.trip import Place, TripRequest

_DECAY = 0.9


async def get_preferences(session: AsyncSession, user_id: str | None) -> list[dict]:
    """Top preference signals for a user (highest weight first)."""
    if not user_id:
        return []
    rows = await session.execute(
        select(Preference)
        .where(Preference.user_id == user_id)
        .order_by(Preference.weight.desc())
        .limit(12)
    )
    return [
        {"key": r.key, "value": r.value, "weight": r.weight} for r in rows.scalars()
    ]


async def record_trip_signals(
    session: AsyncSession, user_id: str | None, req: TripRequest, places: list[Place]
) -> None:
    if not user_id:
        return
    signals: list[tuple[str, str]] = [
        ("budget_level", req.budget_level.value),
        ("region", req.destination.lower()),
    ]
    signals += [("interest", i.lower()) for i in req.interests]
    for cat, _ in Counter(p.category for p in places).most_common(3):
        signals.append(("category", cat))

    existing = {
        (p.key, p.value): p
        for p in (
            await session.execute(
                select(Preference).where(Preference.user_id == user_id)
            )
        ).scalars()
    }
    for pref in existing.values():  # recency decay
        pref.weight *= _DECAY

    for key, value in signals:
        current = existing.get((key, value))
        if current:
            current.weight += 1.0
        else:
            session.add(
                Preference(user_id=user_id, key=key, value=value, weight=1.0)
            )
