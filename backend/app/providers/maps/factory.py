"""Select the maps provider from configuration (Google if keyed, else ORS+OSM)."""
from __future__ import annotations

from functools import lru_cache

from app.config import settings
from app.providers.maps.base import MapsProvider
from app.providers.maps.google import GoogleMapsProvider
from app.providers.maps.ors import OpenRouteServiceProvider


@lru_cache
def get_maps_provider() -> MapsProvider:
    if settings.google_maps_api_key:
        return GoogleMapsProvider()
    return OpenRouteServiceProvider()
