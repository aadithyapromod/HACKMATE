from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from runner.build import execute_build, BuildResultModel


class BuildResult(BaseModel):
    success: bool = Field(..., example=True)
    exit_code: int = Field(..., example=0)
    logs: str = Field(..., example="Build succeeded")
    preview_url: Optional[str] = Field(default=None, example=None)


def build_project(project_id: str, workspace_path: str) -> BuildResult:
    """Entry point for runner sandbox project compilation and preview startup.

    Args:
        project_id: Unique project identifier.
        workspace_path: Relative or absolute path to the generated project directory.

    Returns:
        BuildResult with success, exit_code, logs, and preview_url.
    """
    res = execute_build(workspace_path)
    return BuildResult(
        success=res.success,
        exit_code=res.exit_code,
        logs=f"Project {project_id}: {res.logs}",
        preview_url=res.preview_url
    )


if __name__ == "__main__":
    print("[HackMate Runner Daemon] Initialized and listening for build tasks...")
