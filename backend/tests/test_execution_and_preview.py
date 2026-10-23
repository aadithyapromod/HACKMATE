import pytest
import time
from pathlib import Path
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.project import Project, ProjectStatus
from app.services.workspace import workspace_service
from app.services.runner_service import runner_service
from app.core.errors import RunnerUnavailableError
from app.config import settings
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_preview_blocked_when_not_ready(client: AsyncClient, db_session: AsyncSession):
    # Create project in BUILDING status
    proj = Project(
        title="Unready Project",
        prompt="A project that has not yet compiled.",
        status=ProjectStatus.BUILDING,
    )
    db_session.add(proj)
    await db_session.commit()
    await db_session.refresh(proj)

    # 1. Check preview metadata
    meta_resp = await client.get(f"/api/v2/projects/{proj.id}/preview")
    assert meta_resp.status_code == 200
    meta = meta_resp.json()
    assert meta["is_ready"] is False
    assert meta["preview_url"] is None

    # 2. Attempt asset fetch -> 409 Conflict
    asset_resp = await client.get(f"/api/v2/projects/{proj.id}/preview/index.html")
    assert asset_resp.status_code == 409


@pytest.mark.asyncio
async def test_preview_serves_ready_project(client: AsyncClient, db_session: AsyncSession):
    proj = Project(
        title="Ready Project",
        prompt="A project that finished compiling successfully.",
        status=ProjectStatus.READY,
    )
    db_session.add(proj)
    await db_session.commit()
    await db_session.refresh(proj)

    # Write mock dist files
    dist_dir = workspace_service.get_project_dir(proj.id) / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    (dist_dir / "index.html").write_text("<!doctype html><html><body><h1>App Ready</h1></body></html>")

    # Fetch asset
    resp = await client.get(f"/api/v2/projects/{proj.id}/preview/index.html")
    assert resp.status_code == 200
    assert "App Ready" in resp.text
    assert "Content-Security-Policy" in resp.headers


@pytest.mark.asyncio
async def test_preview_blocks_path_traversal(client: AsyncClient, db_session: AsyncSession):
    proj = Project(
        title="Ready Project Traversal Check",
        prompt="Checking for traversal blocks in preview endpoint.",
        status=ProjectStatus.READY,
    )
    db_session.add(proj)
    await db_session.commit()
    await db_session.refresh(proj)

    # Traversal attempt
    resp = await client.get(f"/api/v2/projects/{proj.id}/preview/../../secret.txt")
    assert resp.status_code in (403, 404)


@pytest.mark.asyncio
async def test_runner_fails_safely_when_docker_unavailable():
    with patch.object(runner_service, "check_docker_available", new_callable=AsyncMock) as mock_check, \
         patch.object(settings, "ENABLE_LOCAL_DEV_RUNNER", False):
        mock_check.return_value = (False, "Daemon socket not found.")

        with pytest.raises(RunnerUnavailableError, match="Direct host execution is disabled by default"):
            await runner_service.execute_build(
                project_id="test-no-docker",
                workspace_path=Path("nonexistent")
            )


def test_workspace_cleanup_expired(tmp_path: Path):
    from app.services.workspace import WorkspaceService
    ws = WorkspaceService(base_dir=tmp_path)

    old_dir = tmp_path / "old-project"
    old_dir.mkdir()
    (old_dir / "file.txt").write_text("content")

    # Set mtime to 2 days ago
    import os
    two_days_ago = time.time() - (86400 * 2)
    os.utime(old_dir, (two_days_ago, two_days_ago))

    removed = ws.cleanup_expired_workspaces(max_age_seconds=86400)
    assert removed == 1
    assert not old_dir.exists()
