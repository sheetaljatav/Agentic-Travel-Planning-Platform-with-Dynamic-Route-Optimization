"""Per-host async rate limiting via aiolimiter.

Nominatim's usage policy (max 1 req/s) is the strictest and is enforced here.
"""
from __future__ import annotations

from aiolimiter import AsyncLimiter

# (max_rate, time_period_seconds) per host. Default is generous; specific hosts
# are throttled to respect their published policies.
_HOST_RATES: dict[str, tuple[int, float]] = {
    "nominatim.openstreetmap.org": (1, 1.0),
    "api.opentripmap.com": (4, 1.0),
    "api.openrouteservice.org": (4, 1.0),
    "api.open-meteo.com": (6, 1.0),
    "geocoding-api.open-meteo.com": (6, 1.0),
    "en.wikipedia.org": (8, 1.0),
    "restcountries.com": (4, 1.0),
    "test.api.amadeus.com": (2, 1.0),
}
_DEFAULT_RATE = (8, 1.0)

_limiters: dict[str, AsyncLimiter] = {}


def limiter_for(host: str) -> AsyncLimiter:
    if host not in _limiters:
        rate, period = _HOST_RATES.get(host, _DEFAULT_RATE)
        _limiters[host] = AsyncLimiter(rate, period)
    return _limiters[host]
