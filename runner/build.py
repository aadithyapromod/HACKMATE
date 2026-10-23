import json
import os
import re
import subprocess
from pathlib import Path
from typing import List, Optional
try:
    from pydantic import BaseModel, Field
except ImportError:
    class BaseModel:  # type: ignore
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

        def model_dump(self):
            return vars(self)

        def dict(self):
            return vars(self)

    def Field(*args, **kwargs):  # type: ignore
        return None


MAX_LOG_SIZE = 100_000  # 100 KB max captured log output
DEFAULT_TIMEOUT = 300   # 5 minutes max build execution


class BuildResultModel(BaseModel):
    success: bool = Field(..., description="Whether build succeeded")
    exit_code: int = Field(..., description="Process exit code")
    logs: str = Field(..., description="Captured stdout and stderr")
    preview_url: Optional[str] = Field(default=None, description="Active preview URL")
    image_tag: Optional[str] = Field(default=None, description="Docker image tag if build succeeded")


def validate_project_id(project_id: str) -> str:
    """Validates that project_id is safe for container names and file paths."""
    if not project_id or not isinstance(project_id, str):
        raise ValueError("Project ID must be a non-empty string.")
    cleaned = project_id.strip()
    if not re.match(r"^[a-zA-Z0-9_-]+$", cleaned):
        raise ValueError(
            f"Invalid project ID '{project_id}'. Only alphanumeric characters, dashes, and underscores are permitted."
        )
    if len(cleaned) > 64:
        raise ValueError("Project ID must not exceed 64 characters.")
    return cleaned


def validate_workspace_path(workspace_path: str, allowed_roots: Optional[List[Path]] = None) -> Path:
    """Validates that workspace_path exists, is a directory, and does not escape allowed roots."""
    if not workspace_path:
        raise ValueError("Workspace path must be provided.")

    raw_path = Path(workspace_path)

    # 1. Reject explicit directory traversal components
    if ".." in raw_path.parts:
        raise ValueError(f"Path traversal ('..') detected in workspace path: '{workspace_path}'")

    path = raw_path.resolve()

    # 2. Check path existence and directory type
    if not path.exists():
        raise ValueError(f"Workspace path does not exist: '{workspace_path}'")
    if not path.is_dir():
        raise ValueError(f"Workspace path is not a directory: '{workspace_path}'")

    # 3. Check containment within allowed roots
    if allowed_roots is None:
        repo_root = Path(__file__).resolve().parent.parent
        allowed_roots = [
            (repo_root / "generated").resolve(),
            (repo_root / "sandbox").resolve(),
            (repo_root / "workspace").resolve(),
        ]

    contained = False
    for root in allowed_roots:
        try:
            path.relative_to(root)
            contained = True
            break
        except ValueError:
            continue

    if not contained:
        raise ValueError(f"Workspace path '{workspace_path}' escapes the approved workspace boundary.")

    return path


def validate_react_vite_project(project_dir: Path) -> None:
    """Ensures the directory adheres to the agreed React + Vite project layout."""
    pkg_file = project_dir / "package.json"
    if not pkg_file.is_file():
        raise ValueError(f"Missing required 'package.json' in {project_dir}")

    try:
        data = json.loads(pkg_file.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"Failed to parse 'package.json' as JSON: {exc}")

    scripts = data.get("scripts", {})
    if not isinstance(scripts, dict) or "build" not in scripts:
        raise ValueError("'package.json' must define a 'build' script (e.g., 'vite build').")

    # Verify React and Vite stack agreement
    deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
    has_vite = "vite" in deps or (project_dir / "vite.config.js").is_file() or (project_dir / "vite.config.ts").is_file()
    has_react = "react" in deps
    if not (has_vite and has_react):
        raise ValueError(
            "Project does not conform to the required React + Vite stack (requires 'react' and 'vite')."
        )


def run_command(args: List[str], timeout: int = DEFAULT_TIMEOUT) -> tuple[int, str]:
    """Runs a command and safely captures stdout and stderr."""
    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        output = (proc.stdout + proc.stderr).strip()
        if len(output) > MAX_LOG_SIZE:
            output = output[:MAX_LOG_SIZE] + f"\n... [Log truncated: exceeded {MAX_LOG_SIZE} bytes]"
        return proc.returncode, output
    except FileNotFoundError:
        return 127, f"Executable not found: {args[0]}"
    except subprocess.TimeoutExpired:
        return 124, f"Command '{' '.join(args)}' timed out after {timeout} seconds."


def execute_build(
    workspace_path: str,
    project_id: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
    allowed_roots: Optional[List[Path]] = None,
) -> BuildResultModel:
    """Executes build tasks inside an isolated Docker container.

    Host execution of untrusted generated code is strictly prohibited.
    """
    # 1. Validate paths and IDs
    try:
        safe_path = validate_workspace_path(workspace_path, allowed_roots)
    except ValueError as err:
        return BuildResultModel(
            success=False,
            exit_code=1,
            logs=f"[Validation Error] Project folder or package.json not found: {err}",
            preview_url=None,
        )

    clean_id = project_id or safe_path.name
    try:
        clean_id = validate_project_id(clean_id)
    except ValueError as err:
        return BuildResultModel(
            success=False,
            exit_code=1,
            logs=f"[Validation Error] {err}",
            preview_url=None,
        )

    # 2. Validate React + Vite layout
    try:
        validate_react_vite_project(safe_path)
    except ValueError as err:
        return BuildResultModel(
            success=False,
            exit_code=1,
            logs=f"[Structure Error] Project folder or package.json not found: {err}",
            preview_url=None,
        )

    # 3. Locate preview Dockerfile
    dockerfile = Path(__file__).resolve().with_name("preview.Dockerfile")
    if not dockerfile.is_file():
        # Fallback to sandbox/runner.Dockerfile if preview.Dockerfile is not present
        dockerfile = safe_path.parent.parent / "sandbox" / "runner.Dockerfile"
        if not dockerfile.is_file():
            return BuildResultModel(
                success=False,
                exit_code=1,
                logs=f"[Configuration Error] Runner Dockerfile not found at {dockerfile}",
                preview_url=None,
            )

    # 4. Enforce .dockerignore to shield host secrets and speed up context loading
    ignore_file = safe_path / ".dockerignore"
    if not ignore_file.exists():
        ignore_file.write_text(
            "node_modules\ndist\n.git\n.env\n.env.*\n",
            encoding="utf-8",
        )

    # 5. Build image in Docker
    image_tag = f"hackmate-{clean_id.lower()}:local"
    build_cmd = [
        "docker", "build",
        "-f", str(dockerfile),
        "-t", image_tag,
        str(safe_path),
    ]

    code, output = run_command(build_cmd, timeout=timeout)
    if code != 0:
        return BuildResultModel(
            success=False,
            exit_code=code,
            logs=f"BUILD FAILED (Exit Code: {code}):\n{output}",
            preview_url=None,
            image_tag=None,
        )

    return BuildResultModel(
        success=True,
        exit_code=0,
        logs=f"BUILD SUCCEEDED:\n{output}",
        preview_url=None,
        image_tag=image_tag,
    )
