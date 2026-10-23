import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.project import Project, ProjectStatus
from app.services.orchestrator import orchestration_service
from app.services.runner_service import runner_service
from app.services.ai_service import (
    ai_service,
    RequirementsAnalysisSchema,
    ProjectPlanSchema,
    TaskItemSchema,
    GeneratedFileSchema,
)


@pytest.fixture
def mock_ai_pipeline():
    mock_analysis = RequirementsAnalysisSchema(
        target_users=["Developers"],
        goals=["Task management"],
        required_features=["Task cards", "Status toggle"],
        technical_constraints=["React", "Vite", "Tailwind"],
        acceptance_criteria=["Works cleanly"],
    )

    mock_plan = ProjectPlanSchema(
        framework="react-vite",
        summary="A clean task manager",
        tasks=[
            TaskItemSchema(
                id="TASK-1",
                sequence_order=1,
                title="Scaffold",
                description="Setup config files",
                dependencies=[],
                expected_files=["package.json", "vite.config.ts"],
                completion_criteria="Build succeeds"
            )
        ],
        file_manifest=["package.json", "vite.config.ts", "index.html", "src/main.tsx", "src/App.tsx"]
    )

    mock_files = [
        GeneratedFileSchema(file_path="package.json", content='{"name": "app", "scripts": {"build": "vite build"}}', language="json"),
        GeneratedFileSchema(file_path="vite.config.ts", content="export default {};", language="typescript"),
        GeneratedFileSchema(file_path="index.html", content="<html><body><script type='module' src='/src/main.tsx'></script></body></html>", language="html"),
        GeneratedFileSchema(file_path="src/main.tsx", content="import App from './App';", language="typescript"),
        GeneratedFileSchema(file_path="src/App.tsx", content="export default function App() { return <div>App</div>; }", language="typescript"),
    ]

    return mock_analysis, mock_plan, mock_files


@pytest.mark.asyncio
async def test_pipeline_execution_success(client: AsyncClient, db_session: AsyncSession, mock_ai_pipeline):
    mock_analysis, mock_plan, mock_files = mock_ai_pipeline

    create_resp = await client.post("/api/v2/projects", json={
        "prompt": "Create an interactive personal task management dashboard with categories and priorities."
    })
    assert create_resp.status_code == 201
    project_id = create_resp.json()["id"]

    with patch.object(runner_service, "execute_build", new_callable=AsyncMock) as mock_build, \
         patch.object(ai_service, "analyze_requirements", new_callable=AsyncMock) as mock_analyze, \
         patch.object(ai_service, "generate_plan", new_callable=AsyncMock) as mock_plan_fn, \
         patch.object(ai_service, "generate_codebase", new_callable=AsyncMock) as mock_codegen:

        mock_build.return_value = (True, 0, "")
        mock_analyze.return_value = mock_analysis
        mock_plan_fn.return_value = mock_plan
        mock_codegen.return_value = mock_files

        start_resp = await client.post(f"/api/v2/projects/{project_id}/start")
        assert start_resp.status_code == 200

        task = orchestration_service._running_tasks.get(project_id)
        if task:
            await task

    # Verify project reached READY state
    get_resp = await client.get(f"/api/v2/projects/{project_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["status"] == "READY"
    assert data["preview_url"] is not None
    assert len(data["tasks"]) > 0

    # Verify files were generated and can be retrieved
    files_resp = await client.get(f"/api/v2/projects/{project_id}/files")
    assert files_resp.status_code == 200
    files_data = files_resp.json()
    assert files_data["total_files"] == 5


@pytest.mark.asyncio
async def test_pipeline_cancellation(client: AsyncClient, db_session: AsyncSession, mock_ai_pipeline):
    mock_analysis, mock_plan, mock_files = mock_ai_pipeline

    create_resp = await client.post("/api/v2/projects", json={
        "prompt": "Build an AI powered recipe recommendation engine with filters."
    })
    project_id = create_resp.json()["id"]

    with patch.object(runner_service, "execute_build", new_callable=AsyncMock) as mock_build, \
         patch.object(ai_service, "analyze_requirements", new_callable=AsyncMock) as mock_analyze, \
         patch.object(ai_service, "generate_plan", new_callable=AsyncMock) as mock_plan_fn, \
         patch.object(ai_service, "generate_codebase", new_callable=AsyncMock) as mock_codegen:

        mock_build.return_value = (True, 0, "")
        mock_analyze.return_value = mock_analysis
        mock_plan_fn.return_value = mock_plan
        mock_codegen.return_value = mock_files

        await client.post(f"/api/v2/projects/{project_id}/start")
        cancel_resp = await client.post(f"/api/v2/projects/{project_id}/cancel")
        assert cancel_resp.status_code in [200, 400]


@pytest.mark.asyncio
async def test_recover_interrupted_projects(db_session: AsyncSession):
    interrupted_project = Project(
        title="Dangling Build",
        prompt="A project that was abruptly terminated when server crashed.",
        status=ProjectStatus.BUILDING,
    )
    db_session.add(interrupted_project)
    await db_session.commit()
    await db_session.refresh(interrupted_project)

    count = await orchestration_service.recover_interrupted_projects()
    assert count >= 1

    await db_session.refresh(interrupted_project)
    assert interrupted_project.status == ProjectStatus.FAILED
    assert "interrupted by a server restart" in interrupted_project.error_message
