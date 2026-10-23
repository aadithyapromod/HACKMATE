import pytest
from pathlib import Path
from app.core.security import sanitize_relative_path, validate_workspace_path
from app.core.errors import SecurityViolationError


def test_sanitize_valid_paths():
    assert sanitize_relative_path("src/App.tsx") == "src/App.tsx"
    assert sanitize_relative_path("package.json") == "package.json"
    assert sanitize_relative_path("src\\components\\Button.tsx") == "src/components/Button.tsx"
    assert sanitize_relative_path("./src/main.tsx") == "src/main.tsx"


def test_sanitize_rejects_directory_traversal():
    with pytest.raises(SecurityViolationError, match="Directory traversal"):
        sanitize_relative_path("../secret.env")

    with pytest.raises(SecurityViolationError, match="Directory traversal"):
        sanitize_relative_path("src/../../etc/passwd")


def test_sanitize_rejects_absolute_paths():
    with pytest.raises(SecurityViolationError, match="Absolute paths are forbidden"):
        sanitize_relative_path("/etc/shadow")

    with pytest.raises(SecurityViolationError, match="Absolute paths are forbidden"):
        sanitize_relative_path("C:/Windows/System32/cmd.exe")


def test_sanitize_rejects_null_bytes():
    with pytest.raises(SecurityViolationError, match="Null byte detected"):
        sanitize_relative_path("src/App.tsx\x00.exe")


def test_sanitize_rejects_disallowed_extensions():
    with pytest.raises(SecurityViolationError, match="File extension '.exe' is not permitted"):
        sanitize_relative_path("src/malicious.exe")

    with pytest.raises(SecurityViolationError, match="File extension '.sh' is not permitted"):
        sanitize_relative_path("src/exploit.sh")


def test_validate_workspace_path_boundaries(tmp_path: Path):
    base_dir = tmp_path / "workspace"
    base_dir.mkdir()

    safe_target = base_dir / "project-1" / "src" / "App.tsx"
    validated = validate_workspace_path(base_dir, safe_target)
    assert validated == safe_target.resolve()

    unsafe_target = tmp_path / "outside_root.txt"
    with pytest.raises(SecurityViolationError, match="Path breakout attempt detected"):
        validate_workspace_path(base_dir, unsafe_target)
