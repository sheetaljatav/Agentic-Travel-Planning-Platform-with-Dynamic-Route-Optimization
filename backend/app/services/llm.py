"""Planner decomposition: turn a natural-language query into a structured
TripRequest + task plan.

Primary path: ChatAnthropic structured output (memory-aware via injected
preferences). Fallback path: a deterministic rule-based parser used whenever no
LLM key is configured or the model call fails — so the platform always runs.
"""
from __future__ import annotations

import logging
import re
from typing import Literal

from pydantic import BaseModel, Field

from app.config import settings
from app.schemas.trip import BudgetLevel, TransportMode, TripRequest

log = logging.getLogger("planner")

_INTEREST_KEYS = [
    "beach", "history", "historic", "heritage", "culture", "museum", "art",
    "nature", "wildlife", "food", "temple", "religion", "nightlife", "adventure",
]
# Capitalized tokens that are never a destination city.
_NON_CITY_CAPS = {
    "plan", "book", "find", "show", "get", "create", "i", "we", "a", "an", "the",
    "and", "or", "with", "for", "my", "our", "your", "day", "days", "trip",
    "budget", "from", "to", "under", "weekend", "quick", "short", "long",
}


class PlannerExtraction(BaseModel):
    origin: str = Field(default="Bangalore")
    destination: str = Field(default="Goa")
    days: int = Field(default=3, ge=1, le=21)
    travelers: int = Field(default=2, ge=1, le=20)
    budget_cap: float = Field(default=25000, ge=0)
    currency: str = "INR"
    budget_level: Literal["budget", "mid", "premium"] = "budget"
    transport_mode: Literal["air", "rail", "road"] = "air"
    interests: list[str] = Field(default_factory=list)
    start_date: str | None = None


def _task_plan(req: TripRequest) -> list[str]:
    return [
        f"Discover attractions in {req.destination} matching interests "
        f"{req.interests or '[general]'}",
        f"Fetch the weather forecast for the {req.days}-day window",
        "Build a travel-time matrix and optimize the daily visiting route",
        f"Estimate total cost against the {req.currency} {int(req.budget_cap):,} cap",
        f"Suggest hotel/transport bookings for {req.origin} -> {req.destination}",
    ]


def _prefs_text(preferences: list[dict]) -> str:
    if not preferences:
        return "No prior preferences on file."
    parts = [f"{p['key']}={p['value']}" for p in preferences[:8]]
    return "Known traveler preferences (most relevant first): " + ", ".join(parts)


async def decompose_query(
    raw_query: str, preferences: list[dict] | None = None
) -> tuple[TripRequest, list[str]]:
    preferences = preferences or []
    extraction = await _extract(raw_query, preferences)
    req = TripRequest(
        raw_query=raw_query,
        origin=extraction.origin,
        destination=extraction.destination,
        days=extraction.days,
        travelers=extraction.travelers,
        budget_cap=extraction.budget_cap,
        currency=extraction.currency,
        budget_level=BudgetLevel(extraction.budget_level),
        transport_mode=TransportMode(extraction.transport_mode),
        interests=extraction.interests,
        start_date=_parse_date(extraction.start_date),
    )
    _apply_preferences(req, preferences)
    return req, _task_plan(req)


async def _extract(raw_query: str, preferences: list[dict]) -> PlannerExtraction:
    if not settings.llm_enabled:
        return _rule_based(raw_query)
    try:
        from langchain_anthropic import ChatAnthropic

        llm = ChatAnthropic(
            model=settings.llm_planner_model,
            api_key=settings.anthropic_api_key,
            temperature=0,
            max_tokens=600,
        )
        structured = llm.with_structured_output(PlannerExtraction)
        system = (
            "You extract structured trip parameters from a traveler's request. "
            "Currency defaults to INR for Indian trips. Infer budget_level from the "
            "per-person daily spend. " + _prefs_text(preferences)
        )
        result = await structured.ainvoke(
            [("system", system), ("human", raw_query)]
        )
        return result  # type: ignore[return-value]
    except Exception as exc:  # noqa: BLE001 - any LLM failure -> deterministic path
        log.warning("LLM extraction failed (%s); using rule-based parser", exc)
        return _rule_based(raw_query)


# ---------------------------------------------------------------- rule-based

_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _parse_date(value: str | None):
    from datetime import date

    if value and _DATE_RE.fullmatch(value.strip()):
        try:
            return date.fromisoformat(value.strip())
        except ValueError:
            return None
    return None


def _clean_city(raw: str) -> str:
    return " ".join(w.capitalize() for w in raw.strip().split())


def _parse_budget(text: str) -> float:
    # Match amounts near currency / "under" cues, supporting "25k" and "25,000".
    for m in re.finditer(
        r"(?:₹|rs\.?|inr|under|below|within|budget(?:\s+of)?)\s*([\d,]+)\s*(k)?",
        text,
    ):
        num = float(m.group(1).replace(",", ""))
        if m.group(2):
            num *= 1000
        return num
    km = re.search(r"\b(\d+)\s*k\b", text)
    if km:
        return float(km.group(1)) * 1000
    return 25000.0


def _rule_based(raw_query: str) -> PlannerExtraction:
    text = raw_query.lower()
    stripped = re.sub(r"\b\d+\s*-?\s*day(s)?\b", " ", text)  # drop "4-day" before city match

    days_m = re.search(r"(\d+)\s*-?\s*day", text)
    days = int(days_m.group(1)) if days_m else 3

    origin_pat = r"from\s+([a-z][a-z\s]+?)(?:\s+(?:to|for|under|with|in|on|by|and)\b|[,.]|$)"
    origin_m = re.search(origin_pat, text)
    origin = _clean_city(origin_m.group(1)) if origin_m else "Bangalore"

    interests = [k for k in _INTEREST_KEYS if k in text]
    dest = _extract_destination(raw_query, stripped, origin, set(interests))

    travelers = 2
    if "solo" in text:
        travelers = 1
    elif "family" in text:
        travelers = 4
    elif "couple" in text:
        travelers = 2
    tm = re.search(r"(\d+)\s*(?:people|persons|adults|travellers|travelers|pax)", text)
    if tm:
        travelers = int(tm.group(1))

    transport = TransportMode.air.value
    if re.search(r"\btrain|rail\b", text):
        transport = TransportMode.rail.value
    elif re.search(r"\bdrive|road\s*trip|by road|self[- ]drive\b", text):
        transport = TransportMode.road.value

    budget_cap = _parse_budget(text)
    if "luxury" in text or "premium" in text:
        level = "premium"
    elif "budget" in text or "cheap" in text or "backpack" in text:
        level = "budget"
    else:
        per_day_pp = budget_cap / max(days, 1) / max(travelers, 1)
        level = "budget" if per_day_pp < 2500 else "mid" if per_day_pp < 5000 else "premium"

    return PlannerExtraction(
        origin=origin,
        destination=dest,
        days=days,
        travelers=travelers,
        budget_cap=budget_cap,
        currency="INR",
        budget_level=level,  # type: ignore[arg-type]
        transport_mode=transport,  # type: ignore[arg-type]
        interests=interests,
    )


def _extract_destination(
    raw_query: str, stripped: str, origin: str, interest_set: set[str]
) -> str:
    """Best-effort destination city for the rule-based fallback."""
    # 1. Explicit "to <city>" phrasing.
    for pat in (
        r"trip to\s+([a-z][a-z\s]+?)(?:\s+(?:under|for|from|with|in|costing)\b|[,.]|$)",
        r"\bto\s+([a-z][a-z\s]+?)(?:\s+(?:under|for|trip|with|in)\b|[,.]|$)",
    ):
        m = re.search(pat, stripped)
        if m:
            cand = m.group(1).strip()
            if cand and cand != origin.lower():
                return _clean_city(cand)

    # 2. First capitalized proper noun that isn't the origin / filler / an interest.
    for cap in re.findall(r"\b([A-Z][a-zA-Z]+)\b", raw_query):
        low = cap.lower()
        if low in _NON_CITY_CAPS or low in interest_set or low == origin.lower():
            continue
        return cap

    # 3. First meaningful word among those preceding "trip".
    m = re.search(r"((?:[a-z]+\s+){0,4})trip\b", stripped)
    if m:
        for word in m.group(1).split():
            if word not in interest_set and word not in _NON_CITY_CAPS and word != origin.lower():
                return _clean_city(word)

    # 4. "in <city>".
    m = re.search(r"\bin\s+([a-z][a-z\s]+?)(?:\s+(?:under|for|from)\b|[,.]|$)", stripped)
    if m and m.group(1).strip() != origin.lower():
        return _clean_city(m.group(1))

    return "Goa"


def _apply_preferences(req: TripRequest, preferences: list[dict]) -> None:
    """Fill gaps from memory: add preferred interests not already requested."""
    if not preferences:
        return
    preferred = [p["value"] for p in preferences if p["key"] == "interest"]
    for interest in preferred:
        if interest not in req.interests:
            req.interests.append(interest)
