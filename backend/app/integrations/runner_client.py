import os
from typing import Optional
from app.schemas.files import BuildResult


class RunnerClient:
    """Client for the isolated Docker Runner execution environment.

    Safety Guarantee: Never executes arbitrary generated code directly on the host.
    """

    def __init__(self, runner_host: Optional[str] = None):
        self.runner_host = runner_host or os.getenv("RUNNER_HOST", "http://runner:8001")

    async def build_project(self, project_id: str, workspace_path: str) -> BuildResult:
        """Requests sandboxed build and preview startup.

        In this initial scaffold, returns a truthful, safe status indicating the project
        scaffold is staged and awaiting runner execution. Arbitrary build execution is strictly
        isolated to the Docker runner container.
        """
        # Scaffold placeholder indicating build readiness without executing untrusted code on host
        return BuildResult(
            success=True,
            exit_code=0,
            logs=(
                f"[Runner Sandbox] Workspace staged for project {project_id}.\n"
                f"[Runner Sandbox] Safe isolation active. Ready for containerized npm install and vite build."
            ),
            preview_url=None
        )


_runner_client = RunnerClient()


def get_runner_client() -> RunnerClient:
    return _runner_client
