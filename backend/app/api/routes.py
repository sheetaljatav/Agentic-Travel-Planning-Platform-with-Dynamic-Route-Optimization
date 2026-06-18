"""HTTP API: plan generation, retrieval, and health."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.providers.maps.factory import get_maps_provider
from app.schemas.trip import ItineraryOut, PlanRequestIn
from app.services import pipeline, store

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "llm_enabled": settings.llm_enabled,
        "maps_provider": get_maps_provider().name,
        "opentripmap": bool(settings.opentripmap_api_key),
        "amadeus": bool(settings.amadeus_client_id and settings.amadeus_client_secret),
    }


@router.post("/api/plan", response_model=ItineraryOut)
async def create_plan(
    body: PlanRequestIn, session: AsyncSession = Depends(get_session)
) -> ItineraryOut:
    query = body.query.strip()
    if not query:
        raise HTTPException(status_code=422, detail="query must not be empty")
    return await pipeline.generate_itinerary(session, query, body.user_id)


@router.get("/api/plan/{trip_id}", response_model=ItineraryOut)
async def get_plan(
    trip_id: str, session: AsyncSession = Depends(get_session)
) -> ItineraryOut:
    data = await store.get_itinerary(session, trip_id)
    if not data:
        raise HTTPException(status_code=404, detail="itinerary not found")
    return ItineraryOut(**data)
