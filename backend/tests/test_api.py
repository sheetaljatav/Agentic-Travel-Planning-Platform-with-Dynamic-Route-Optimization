import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_plan_create_and_fetch(stub_external):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"

        resp = await client.post(
            "/api/plan",
            json={
                "query": "Plan a 4-day Goa trip under ₹25,000 from Bangalore",
                "user_id": "u1",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        trip_id = data["trip_id"]
        assert data["request"]["destination"] == "Goa"
        assert data["within_budget"] is True
        assert len(data["bookings"]) >= 2

        fetched = await client.get(f"/api/plan/{trip_id}")
        assert fetched.status_code == 200
        assert fetched.json()["trip_id"] == trip_id


@pytest.mark.asyncio
async def test_missing_plan_returns_404():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/plan/does-not-exist")
        assert resp.status_code == 404
