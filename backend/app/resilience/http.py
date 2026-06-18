"""Single layered async HTTP-JSON fetch.

Composition order (mirrors legacy util/fetch.ts):
    host allowlist -> rate limiter -> circuit breaker -> timeout -> retry
with exponential backoff + jitter and Retry-After header respect.

Every external tool calls `fetch_json` so resilience lives in exactly one place.
"""
from __future__ import annotations

import asyncio
import random
from typing import Any
from urllib.parse import urlparse

import httpx

from app.config import settings
from app.resilience.breaker import breaker
from app.resilience.errors import ExternalFetchError
from app.resilience.limiter import limiter_for

# Security: only these hosts may be contacted (free providers + optional paid).
ALLOWED_HOSTS: set[str] = {
    "nominatim.openstreetmap.org",
    "api.opentripmap.com",
    "api.openrouteservice.org",
    "api.open-meteo.com",
    "geocoding-api.open-meteo.com",
    "en.wikipedia.org",
    "restcountries.com",
    "test.api.amadeus.com",
    "api.amadeus.com",
    "open.er-api.com",
    "api.frankfurter.app",
    "maps.googleapis.com",
}

_RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}

_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.http_timeout_s),
            limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
            follow_redirects=True,
            headers={"User-Agent": settings.nominatim_user_agent},
        )
    return _client


async def close_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def _retry_after_seconds(resp: httpx.Response) -> float | None:
    raw = resp.headers.get("retry-after")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


async def fetch_json(
    url: str,
    *,
    method: str = "GET",
    params: dict[str, Any] | None = None,
    json: Any = None,
    data: Any = None,
    headers: dict[str, str] | None = None,
    timeout_s: float | None = None,
    max_retries: int | None = None,
) -> Any:
    host = urlparse(url).hostname or ""
    if host not in ALLOWED_HOSTS:
        raise ExternalFetchError("blocked", f"host not allowed: {host}", host=host)

    retries = settings.http_max_retries if max_retries is None else max_retries
    timeout = settings.http_timeout_s if timeout_s is None else timeout_s
    client = get_client()
    last_exc: Exception | None = None

    for attempt in range(retries + 1):
        async with limiter_for(host):
            breaker.before(host)
            try:
                resp = await client.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    data=data,
                    headers=headers,
                    timeout=timeout,
                )
            except httpx.TimeoutException as exc:
                last_exc = ExternalFetchError("timeout", str(exc), host=host)
                breaker.on_failure(host)
            except httpx.HTTPError as exc:
                last_exc = ExternalFetchError("network", str(exc), host=host)
                breaker.on_failure(host)
            else:
                if resp.status_code < 400:
                    breaker.on_success(host)
                    if not resp.content:
                        return None
                    return resp.json()
                if resp.status_code in _RETRYABLE_STATUS:
                    if resp.status_code >= 500:
                        breaker.on_failure(host)
                    last_exc = ExternalFetchError(
                        "http", f"status {resp.status_code}", host=host, status=resp.status_code
                    )
                    wait = _retry_after_seconds(resp)
                    if wait is not None and attempt < retries:
                        await asyncio.sleep(min(wait, 10.0))
                        continue
                else:
                    # Non-retryable client error -> fail fast.
                    raise ExternalFetchError(
                        "http", f"status {resp.status_code}", host=host, status=resp.status_code
                    )

        if attempt < retries:
            backoff = min(0.2 * (2**attempt), 5.0) + random.uniform(0, 0.2)
            await asyncio.sleep(backoff)

    assert last_exc is not None
    raise last_exc
