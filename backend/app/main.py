"""FastAPI application entrypoint."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import settings
from app.db import init_db
from app.resilience.http import close_client

logging.basicConfig(level=settings.log_level.upper())


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev convenience: ensure tables exist. Prod schema is owned by Alembic.
    try:
        await init_db()
    except Exception as exc:  # noqa: BLE001 - app still serves /health if DB is down
        logging.getLogger("startup").warning("init_db skipped: %s", exc)
    yield
    await close_client()


app = FastAPI(
    title="Agentic Travel Planning Platform",
    version="1.0.0",
    description="Multi-agent (LangGraph) itinerary planner with dynamic route optimization.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    # No cookies/auth are used, so credentials stay off — this lets CORS_ORIGINS="*"
    # work for any deployed frontend without per-origin configuration.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

# Single-service deploy: serve the built React app if a dist dir is provided.
# API routes (/api/*, /health) are registered above, so they take precedence
# over this catch-all static mount.
if settings.frontend_dist and os.path.isdir(settings.frontend_dist):
    app.mount(
        "/", StaticFiles(directory=settings.frontend_dist, html=True), name="frontend"
    )
