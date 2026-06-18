"""Centralized configuration via pydantic-settings.

All API keys are optional; the platform selects free providers / heuristic
fallbacks when a key is absent, so it always runs end-to-end.
"""
from __future__ import annotations

import re
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Core
    app_env: str = "development"
    log_level: str = "info"
    cors_origins: str = "http://localhost:5173"

    # Database
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/travel"
    )

    # LLM
    anthropic_api_key: str = ""
    llm_planner_model: str = "claude-opus-4-8"
    llm_extract_model: str = "claude-haiku-4-5"
    llm_openai_base_url: str = ""
    llm_openai_api_key: str = ""

    # Maps
    google_maps_api_key: str = ""
    ors_api_key: str = ""
    nominatim_user_agent: str = "agentic-travel-planner/1.0"

    # POI
    opentripmap_api_key: str = ""

    # Amadeus
    amadeus_client_id: str = ""
    amadeus_client_secret: str = ""
    amadeus_base_url: str = "https://test.api.amadeus.com"

    # FX
    fx_base_url: str = "https://open.er-api.com/v6/latest"

    # Optional: directory of a built React app for the backend to serve (single
    # service deploy). Empty -> API only (frontend hosted separately).
    frontend_dist: str = ""

    # Resilience
    http_timeout_s: float = 8.0
    http_max_retries: int = 3
    breaker_fail_threshold: int = 5
    breaker_reset_s: float = 30.0

    @model_validator(mode="after")
    def _normalize_database_url(self) -> Settings:
        url = self.database_url
        # Managed Postgres (Render/Heroku/Neon) emits postgres:// — map to asyncpg.
        if url.startswith("postgres://"):
            url = "postgresql+asyncpg://" + url[len("postgres://"):]
        elif url.startswith("postgresql://"):
            url = "postgresql+asyncpg://" + url[len("postgresql://"):]
        # asyncpg rejects libpq's sslmode query param; strip it.
        if "+asyncpg" in url:
            url = re.sub(r"[?&]sslmode=[^&]*", "", url)
        self.database_url = url
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def llm_enabled(self) -> bool:
        return bool(self.anthropic_api_key or self.llm_openai_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
