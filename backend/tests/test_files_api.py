import pytest
import io
import zipfile
from httpx import AsyncClient
from app.services.workspace import workspace_service
from app.models.file import GeneratedFile
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_files_api_lifecycle(client: AsyncClient, db_session: AsyncSession):
    # 1. Create a project
    create_resp = await client.post("/api/v2/projects", json={
        "prompt": "Interactive portfolio site with three project cards and contact form."
    })
    assert create_resp.status_code == 201
    project_id = create_resp.json()["id"]

    # 2. Write test files to workspace and DB
    workspace_service.write_file(project_id, "package.json", '{"name": "test-pkg"}')
    workspace_service.write_file(project_id, "src/App.tsx", 'export default function App() { return <div>App</div>; }')

    f1 = GeneratedFile(
        project_id=project_id,
        file_path="package.json",
        content='{"name": "test-pkg"}',
        language="json",
        file_size_bytes=20,
    )
    f2 = GeneratedFile(
        project_id=project_id,
        file_path="src/App.tsx",
        content='export default function App() { return <div>App</div>; }',
        language="typescript",
        file_size_bytes=56,
    )
    db_session.add(f1)
    db_session.add(f2)
    await db_session.commit()

    # 3. List files
    list_resp = await client.get(f"/api/v2/projects/{project_id}/files")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total_files"] == 2
    paths = [f["file_path"] for f in list_data["files"]]
    assert "package.json" in paths
    assert "src/App.tsx" in paths

    # 4. Read single file
    file_resp = await client.get(f"/api/v2/projects/{project_id}/files/src/App.tsx")
    assert file_resp.status_code == 200
    file_data = file_resp.json()
    assert file_data["file_path"] == "src/App.tsx"
    assert "export default function App" in file_data["content"]

    # 5. Export ZIP archive
    zip_resp = await client.get(f"/api/v2/projects/{project_id}/export")
    assert zip_resp.status_code == 200
    assert zip_resp.headers["content-type"] == "application/zip"

    zip_bytes = io.BytesIO(zip_resp.content)
    with zipfile.ZipFile(zip_bytes, "r") as zf:
        namelist = zf.namelist()
        assert "package.json" in namelist
        assert "src/App.tsx" in namelist


@pytest.mark.asyncio
async def test_get_nonexistent_file(client: AsyncClient):
    create_resp = await client.post("/api/v2/projects", json={
        "prompt": "Test project for non existent file retrieval check."
    })
    project_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v2/projects/{project_id}/files/missing.ts")
    assert resp.status_code == 404
