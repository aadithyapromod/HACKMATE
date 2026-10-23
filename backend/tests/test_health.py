import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/api/v2/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "timestamp" in data
    assert "services" in data
    assert data["services"]["database"]["status"] == "connected"
    assert "runner" in data["services"]
    assert "configured_type" in data["services"]["runner"]
