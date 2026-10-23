import pytest
from unittest.mock import AsyncMock, patch
from app.services.ai_service import (
    ai_service,
    RequirementsAnalysisSchema,
    ProjectPlanSchema,
    TaskItemSchema,
    ProjectCodebaseSchema,
    GeneratedFileSchema,
    CodeRepairSchema,
)
from app.services.gemini_client import gemini_client, GeminiOutputValidationError
from app.core.errors import SecurityViolationError


@pytest.mark.asyncio
async def test_requirements_analysis_mocked():
    mock_analysis = RequirementsAnalysisSchema(
        target_users=["Freelancers", "Designers"],
        goals=["Build portfolio", "Showcase work"],
        required_features=["Hero banner", "Project grid", "Contact modal"],
        technical_constraints=["React 18", "Vite", "Tailwind CSS"],
        acceptance_criteria=["Renders on mobile", "Filters work"],
        clarifications_needed=None,
    )

    with patch.object(gemini_client, "generate_structured", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_analysis

        result = await ai_service.analyze_requirements("Personal portfolio for a designer")
        assert len(result.target_users) == 2
        assert "Hero banner" in result.required_features
        mock_gen.assert_called_once()


@pytest.mark.asyncio
async def test_planning_mocked():
    mock_plan = ProjectPlanSchema(
        framework="react-vite",
        summary="A responsive portfolio web application",
        tasks=[
            TaskItemSchema(
                id="TASK-1",
                sequence_order=1,
                title="Initialize Scaffold",
                description="Create configuration files",
                dependencies=[],
                expected_files=["package.json", "vite.config.ts"],
                completion_criteria="Build scripts execute"
            )
        ],
        file_manifest=["package.json", "vite.config.ts", "index.html", "src/main.tsx", "src/App.tsx"]
    )

    with patch.object(gemini_client, "generate_structured", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_plan

        analysis = RequirementsAnalysisSchema(
            target_users=["Users"], goals=["Goal"], required_features=["F1"],
            technical_constraints=["C1"], acceptance_criteria=["A1"]
        )
        plan = await ai_service.generate_plan("Prompt", analysis)
        assert len(plan.tasks) == 1
        assert "package.json" in plan.file_manifest


def test_codebase_validation_rejects_missing_entry_points():
    # Missing src/App.tsx
    broken_files = [
        GeneratedFileSchema(file_path="package.json", content='{"name": "test", "scripts": {"build": "vite build"}}', language="json"),
        GeneratedFileSchema(file_path="vite.config.ts", content="export default {};", language="typescript"),
        GeneratedFileSchema(file_path="index.html", content="<html><body><script src='/src/main.tsx'></script></body></html>", language="html"),
        GeneratedFileSchema(file_path="src/main.tsx", content="console.log('main');", language="typescript"),
    ]

    with pytest.raises(GeminiOutputValidationError, match="missing mandatory entry points"):
        ai_service.validate_codebase(broken_files)


def test_codebase_validation_rejects_unsafe_paths():
    unsafe_files = [
        GeneratedFileSchema(file_path="../evil.ts", content="evil code", language="typescript")
    ]
    with pytest.raises(SecurityViolationError, match="Directory traversal"):
        ai_service.validate_codebase(unsafe_files)


def test_codebase_validation_rejects_truncated_files():
    truncated_files = [
        GeneratedFileSchema(file_path="package.json", content='{"name": "app", "scripts": {"build": "vite build"}}', language="json"),
        GeneratedFileSchema(file_path="vite.config.ts", content="export default {};", language="typescript"),
        GeneratedFileSchema(file_path="index.html", content="<html><body><script src='/src/main.tsx'></script></body></html>", language="html"),
        GeneratedFileSchema(file_path="src/main.tsx", content="console.log('main');", language="typescript"),
        GeneratedFileSchema(file_path="src/App.tsx", content="", language="typescript"),  # Empty!
    ]
    with pytest.raises(GeminiOutputValidationError, match="truncated or empty"):
        ai_service.validate_codebase(truncated_files)


@pytest.mark.asyncio
async def test_repair_codebase_mocked():
    initial_files = [
        GeneratedFileSchema(file_path="package.json", content='{"name": "app", "scripts": {"build": "vite build"}}', language="json"),
        GeneratedFileSchema(file_path="src/App.tsx", content="export default function App() { return <div>Broken</div> }", language="typescript"),
    ]

    fixed_file = GeneratedFileSchema(
        file_path="src/App.tsx",
        content="export default function App() { return <div>Fixed App</div>; }",
        language="typescript"
    )

    mock_repair = CodeRepairSchema(
        diagnosis="Missing semicolon and corrected JSX tag",
        fixed_files=[fixed_file]
    )

    with patch.object(gemini_client, "generate_structured", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_repair

        repaired = await ai_service.repair_codebase(
            prompt="Make an app",
            files=initial_files,
            error_log="SyntaxError in src/App.tsx",
            attempt=1
        )

        app_file = next(f for f in repaired if f.file_path == "src/App.tsx")
        assert "Fixed App" in app_file.content
