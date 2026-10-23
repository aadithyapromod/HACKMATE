from ai.planner import create_plan
from ai.generator import generate_files
from ai.models import PlanOutput, FileListOutput


def test_create_plan():
    idea = "Build a student hackathon matching website"
    plan = create_plan(idea)
    assert isinstance(plan, PlanOutput)
    assert plan.framework == "react-vite"
    assert len(plan.tasks) > 0
    assert any("Architecture" in t.title or "Design" in t.title for t in plan.tasks)


def test_generate_files():
    idea = "Build a student hackathon matching website"
    plan = create_plan(idea)
    files_output = generate_files(idea, plan)
    assert isinstance(files_output, FileListOutput)
    assert len(files_output.files) >= 4

    paths = [f.path for f in files_output.files]
    assert "package.json" in paths
    assert "src/App.jsx" in paths
    assert "index.html" in paths
