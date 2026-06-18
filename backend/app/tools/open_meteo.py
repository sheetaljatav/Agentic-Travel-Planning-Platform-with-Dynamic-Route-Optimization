"""Open-Meteo weather forecast + geocoding (free, no key)."""
from __future__ import annotations

from datetime import date as Date
from datetime import timedelta

from app.resilience.errors import ExternalFetchError
from app.resilience.http import fetch_json
from app.schemas.trip import LatLng, WeatherDay

_GEOCODE = "https://geocoding-api.open-meteo.com/v1/search"
_FORECAST = "https://api.open-meteo.com/v1/forecast"

# WMO weather codes -> short human summary (condensed).
_WMO = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Rime fog", 51: "Light drizzle", 53: "Drizzle", 55: "Dense drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain", 71: "Light snow", 73: "Snow",
    75: "Heavy snow", 80: "Rain showers", 81: "Rain showers", 82: "Violent showers",
    95: "Thunderstorm", 96: "Thunderstorm w/ hail", 99: "Severe thunderstorm",
}


async def geocode(city: str) -> LatLng | None:
    try:
        data = await fetch_json(_GEOCODE, params={"name": city, "count": 1})
    except ExternalFetchError:
        return None
    results = (data or {}).get("results") or []
    if not results:
        return None
    top = results[0]
    return LatLng(lat=top["latitude"], lng=top["longitude"])


async def forecast(
    center: LatLng, start: Date | None, days: int
) -> list[WeatherDay]:
    """Daily forecast for `days` starting at `start` (defaults to today)."""
    start = start or Date.today()
    end = start + timedelta(days=max(days - 1, 0))
    try:
        data = await fetch_json(
            _FORECAST,
            params={
                "latitude": center.lat,
                "longitude": center.lng,
                "daily": "weathercode,temperature_2m_max,temperature_2m_min,precipitation_sum",
                "timezone": "auto",
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
            },
        )
    except ExternalFetchError:
        return []
    daily = (data or {}).get("daily") or {}
    out: list[WeatherDay] = []
    for i, day in enumerate(daily.get("time", [])):
        code = (daily.get("weathercode") or [])[i]
        out.append(
            WeatherDay(
                date=Date.fromisoformat(day),
                summary=_WMO.get(code, "Unknown"),
                temp_max_c=(daily.get("temperature_2m_max") or [None])[i],
                temp_min_c=(daily.get("temperature_2m_min") or [None])[i],
                precipitation_mm=(daily.get("precipitation_sum") or [None])[i],
            )
        )
    return out
