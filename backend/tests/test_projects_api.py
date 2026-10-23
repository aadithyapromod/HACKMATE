import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_fetch_project(client: AsyncClient):
    # Valid creation
    payload = {
        "title": "Crypto Portfolio Dashboard",
        "prompt": "Build a responsive crypto analytics dashboard with live price charts and currency converter.",
        "reference_url": "https://example.com/crypto"
    }
    create_resp = await client.post("/api/v2/projects", json=payload)
    assert create_resp.status_code == 201
    created_data = create_resp.json()
    assert created_data["title"] == "Crypto Portfolio Dashboard"
    assert created_data["status"] == "QUEUED"
    assert "id" in created_data
    project_id = created_data["id"]

    # Fetch detail
    get_resp = await client.get(f"/api/v2/projects/{project_id}")
    assert get_resp.status_code == 200
    detail = get_resp.json()
    assert detail["id"] == project_id
    assert detail["status"] == "QUEUED"

    # List projects
    list_resp = await client.get("/api/v2/projects")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] >= 1
    assert any(p["id"] == project_id for p in list_data["items"])


@pytest.mark.asyncio
async def test_create_project_validation_errors(client: AsyncClient):
    # Too short prompt (< 10 chars)
    resp = await client.post("/api/v2/projects", json={"prompt": "short"})
    assert resp.status_code == 422

    # Invalid URL scheme
    resp_url = await client.post("/api/v2/projects", json={
        "prompt": "Valid length prompt here for testing.",
        "reference_url": "ftp://invalid-url.com"
    })
    assert resp_url.status_code == 422


@pytest.mark.asyncio
async def test_nonexistent_project_returns_404(client: AsyncClient):
    resp = await client.get("/api/v2/projects/non-existent-uuid")
    assert resp.status_code == 404
