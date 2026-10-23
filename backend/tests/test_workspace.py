import pytest
import zipfile
from pathlib import Path
from app.services.workspace import WorkspaceService
from app.core.errors import SecurityViolationError


def test_workspace_file_lifecycle(tmp_path: Path):
    ws = WorkspaceService(base_dir=tmp_path)
    project_id = "test-proj-123"

    # Write files
    size1 = ws.write_file(project_id, "package.json", '{"name": "test"}')
    assert size1 > 0

    size2 = ws.write_file(project_id, "src/App.tsx", "export default function App() {}")
    assert size2 > 0

    # Read files
    content = ws.read_file(project_id, "package.json")
    assert '{"name": "test"}' in content

    # List files
    files = ws.list_files(project_id)
    assert files == ["package.json", "src/App.tsx"]

    # ZIP archive
    zip_buf = ws.create_zip_archive(project_id)
    with zipfile.ZipFile(zip_buf, "r") as zf:
        namelist = zf.namelist()
        assert "package.json" in namelist
        assert "src/App.tsx" in namelist

    # Cleanup
    ws.delete_workspace(project_id)
    assert not (tmp_path / project_id).exists()


def test_workspace_rejects_escape(tmp_path: Path):
    ws = WorkspaceService(base_dir=tmp_path)
    with pytest.raises(SecurityViolationError):
        ws.write_file("test-proj-123", "../../escape.txt", "payload")
