from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_create_project_success():
    payload = {"idea": "Build a student hackathon matching website"}
    response = client.post("/api/projects", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["id"].startswith("project-")
    assert data["idea"] == payload["idea"]
    assert data["status"] == "created"
    assert "created_at" in data


def test_create_project_validation_failure():
    # Less than 10 characters after strip
    payload = {"idea": "   too short  "}
    response = client.post("/api/projects", json=payload)
    assert response.status_code == 422  # Pydantic validation error


def test_get_project_success():
    # First create
    create_resp = client.post(
        "/api/projects",
        json={"idea": "A collaborative whiteboard for hackathon teams"},
    )
    assert create_resp.status_code == 201
    proj_id = create_resp.json()["id"]

    # Retrieve
    get_resp = client.get(f"/api/projects/{proj_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == proj_id
    assert get_resp.json()["status"] == "created"


def test_get_project_not_found():
    response = client.get("/api/projects/project-nonexistent")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_tasks_empty():
    create_resp = client.post(
        "/api/projects",
        json={"idea": "Automated AI resume screener for recruiters"},
    )
    proj_id = create_resp.json()["id"]

    tasks_resp = client.get(f"/api/projects/{proj_id}/tasks")
    assert tasks_resp.status_code == 200
    assert tasks_resp.json() == []


def test_get_files_empty():
    create_resp = client.post(
        "/api/projects",
        json={"idea": "Realtime multiplayer code chess competition"},
    )
    proj_id = create_resp.json()["id"]

    files_resp = client.get(f"/api/projects/{proj_id}/files")
    assert files_resp.status_code == 200
    assert files_resp.json() == {"files": []}


def test_start_project_pipeline():
    create_resp = client.post(
        "/api/projects",
        json={"idea": "Smart pantry tracker with barcode scanner"},
    )
    proj_id = create_resp.json()["id"]

    start_resp = client.post(f"/api/projects/{proj_id}/start")
    assert start_resp.status_code == 200
    # Status should truthfully reflect that pipeline has started planning
    assert start_resp.json()["status"] in ["planning", "generating", "completed"]


def test_get_preview():
    create_resp = client.post(
        "/api/projects",
        json={"idea": "Personal finance visualizer with sankey charts"},
    )
    proj_id = create_resp.json()["id"]

    preview_resp = client.get(f"/api/projects/{proj_id}/preview")
    assert preview_resp.status_code == 200
    data = preview_resp.json()
    assert "success" in data
    assert "exit_code" in data
    assert "logs" in data
