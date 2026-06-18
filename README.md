# Agentic Travel Planning Platform with Dynamic Route Optimization

A multi-agent travel planner that turns a natural-language request like
**"Plan a 4-day Goa trip under ₹25,000 from Bangalore"** into a personalized,
route-optimized, budgeted itinerary. Five **LangGraph** agents decompose the
task and orchestrate **10+ external APIs**; independent agents run in parallel
to cut latency.

```
React (Vite)  ──HTTP──▶  FastAPI  ──▶  LangGraph multi-agent graph  ──▶  PostgreSQL
                                          │
                 Planner ─▶ {Places ‖ Weather} ─▶ Routing ─▶ Budget ─(trim?)─▶ Booking ─▶ Assemble
```

## Agents

| Agent | Responsibility | Key tools |
|-------|----------------|-----------|
| **Planner** | Decompose the NL query into a structured `TripRequest` + task plan (memory-aware) | Claude (LangChain) structured output, with a deterministic rule-based fallback |
| **Places** | Discover & rank attractions near the destination | OpenTripMap, Wikipedia, geocoding (Nominatim / Google) |
| **Routing** | Build a travel-time matrix and optimize the visiting order | OpenRouteService / Google Distance-Matrix + local **2-opt** optimizer |
| **Budget** | Line-item cost estimate vs. the cap; trigger re-planning if over | Amadeus (flights/hotels), FX, REST Countries |
| **Booking** | Non-transactional booking suggestions (links + prices) | Amadeus, deep links |

`Places` and `Weather` are independent and execute **concurrently** (graph
fan-out); every tool call is async (`httpx` + `asyncio.gather`). When the
estimate exceeds the cap, the graph autonomously **trims** once (switch to rail,
drop a budget tier, remove the lowest-value stop) and re-optimizes — a bounded
feedback loop.

## Tech stack

- **Backend:** Python 3.10+, FastAPI, LangGraph, LangChain (Anthropic Claude), SQLAlchemy 2 (async) + Alembic, httpx
- **Frontend:** React + Vite + TypeScript (lean: itinerary timeline + budget breakdown)
- **Database:** PostgreSQL (JSONB itineraries + an `agent_runs` orchestration/latency trace)
- **Maps/data:** Google Maps **or** free alternatives (OpenStreetMap/Nominatim, OpenRouteService, OpenTripMap, Open-Meteo, Wikipedia, REST Countries, Amadeus test tier, free FX)

### Live data, free by default
Every data API has a **free, no-billing live default**, so the platform runs
end-to-end with **zero keys**. Set a key to upgrade a provider:

| Capability | Default (free, live) | Upgrade |
|-----------|----------------------|---------|
| Geocoding / routing / matrix | Nominatim + OpenRouteService (`ORS_API_KEY` optional; haversine if absent) | `GOOGLE_MAPS_API_KEY` → Google Maps |
| Attractions | Wikipedia geosearch | `OPENTRIPMAP_API_KEY` → OpenTripMap |
| Weather | Open-Meteo (no key) | — |
| Pricing/booking | Heuristics | `AMADEUS_CLIENT_ID/SECRET` → live fares |
| Planner LLM | Rule-based parser | `ANTHROPIC_API_KEY` → Claude |

## Quick start

### Docker (everything)
```bash
docker compose up --build
# UI:      http://localhost:8080
# API:     http://localhost:8000/health
# (optional) export ANTHROPIC_API_KEY / GOOGLE_MAPS_API_KEY ... before `up`
```

### Local dev
```bash
# backend
cd backend
python -m venv .venv && . .venv/Scripts/activate   # or source .venv/bin/activate
pip install -e ".[dev]"
# point DATABASE_URL at a local Postgres, or use sqlite for a quick spin:
#   export DATABASE_URL="sqlite+aiosqlite:///./dev.db"
uvicorn app.main:app --reload

# frontend (new shell)
cd frontend
npm install
npm run dev        # http://localhost:5173 (proxies /api -> :8000)
```

## API

```bash
curl -s localhost:8000/api/plan -H 'content-type: application/json' \
  -d '{"query":"Plan a 4-day Goa trip under ₹25,000 from Bangalore","user_id":"demo"}'
```
Returns an `ItineraryOut`: day-by-day stops (optimized order) with weather and
travel time, a line-item budget vs. the cap, booking suggestions, and the full
`agent_runs` trace. `GET /api/plan/{trip_id}` re-reads it from Postgres.

## Latency benchmark (the "35%" claim)

Runs the **same** agent nodes wired two ways — `places ‖ weather` vs.
`places → weather` — so the delta is purely the parallel-execution win (no
artificial sleeps in the sequential path):

```bash
cd backend
python -m app.bench.latency            # offline, deterministic stub latencies
python -m app.bench.latency --live     # hit the real free APIs (no keys needed)
```
Representative run (offline, p50 / 6):
```
sequential (places -> weather):     2557 ms
parallel   (places || weather):     1646 ms
improvement:                          35.6%
```

## Deploy (free)

**Frontend → GitHub Pages (automatic).** On every push to `main`, the
[`pages.yml`](.github/workflows/pages.yml) workflow builds the UI in *demo mode*
(a bundled, pre-generated itinerary — works with no backend) and publishes it.
One-time setup: **Settings → Pages → Source = "GitHub Actions"**. Live at:
`https://sheetaljatav.github.io/Agentic-Travel-Planning-Platform-with-Dynamic-Route-Optimization/`

**Full stack → Render (one click, free tier).** [`render.yaml`](render.yaml) is a
Blueprint that provisions a free Postgres + a single web service which serves
**both** the FastAPI API and the built React app (one URL, no CORS):

1. Render → **New → Blueprint** → connect this repo → **Apply**.
2. (Optional) add `OPENTRIPMAP_API_KEY` / `ANTHROPIC_API_KEY` / `GOOGLE_MAPS_API_KEY`
   in the dashboard to upgrade data quality. It runs fully on free providers
   without them.

To point the Pages UI at the live Render backend instead of demo data, rebuild
Pages with `VITE_DEMO` unset and `VITE_API_URL=https://<your-render-app>.onrender.com`.

## Tests & quality

```bash
cd backend
pytest -q          # unit (optimizer, budget, planner), graph integration, API e2e
ruff check app     # lint
```
Tests stub all network I/O (no live calls) and use an in-process SQLite DB.

## Repository layout

```
backend/    FastAPI + LangGraph agents + tools + resilience + Alembic
frontend/   React (Vite + TS) lean UI
Dockerfile  single-image build (frontend served by FastAPI) for Render
render.yaml  one-click free deploy blueprint
docker-compose.yml
```

> Rebuilt from a prior TypeScript app ("Voyant"); that legacy code is kept
> locally for reference but is excluded from this repository.

## Resume mapping

- **Maps API integration** — pluggable `MapsProvider` (Google ⇄ OpenRouteService/OSM); Distance-Matrix + Directions feed routing.
- **Tool calling / agent orchestration** — 5 LangGraph nodes, parallel fan-out, bounded budget feedback loop, structured planner output.
- **Real-world data handling** — 10+ live APIs behind one resilient `fetch_json` (allowlist → rate-limit → circuit-breaker → timeout → retry w/ backoff).
- **35% latency reduction** — measured by `app.bench.latency`.
