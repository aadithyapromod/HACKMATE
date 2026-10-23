import asyncio
import inspect
import json
import os
import sys
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional, Union
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

from runner.build import execute_build, validate_project_id, validate_workspace_path
from runner.preview import start_preview as preview_start, stop_preview as preview_stop


class BuildResult(BaseModel):
    success: bool = Field(..., example=True)
    exit_code: int = Field(..., example=0)
    logs: str = Field(..., example="Build succeeded")
    preview_url: Optional[str] = Field(default=None, example=None)


def build_project_sync(project_id: str, workspace_path: str) -> dict:
    """Synchronous core implementation of project build."""
    res = execute_build(workspace_path=workspace_path, project_id=project_id)
    return {
        "success": res.success,
        "exit_code": res.exit_code,
        "logs": res.logs,
        "preview_url": res.preview_url,
    }


async def build_project(project_id: str, workspace_path: str) -> dict:
    """Async entry point conforming to Phase 2 contracts for building projects.

    Args:
        project_id: Unique project identifier.
        workspace_path: Path to the generated project directory.

    Returns:
        dict with success, exit_code, logs, and preview_url.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, build_project_sync, project_id, workspace_path)


async def start_preview(project_id: str, workspace_path: str, port: Optional[int] = None) -> dict:
    """Async entry point conforming to Phase 2 contracts for starting live previews.

    Args:
        project_id: Unique project identifier.
        workspace_path: Path to the generated project directory.
        port: Optional specific port (binds to 127.0.0.1).

    Returns:
        dict with success, exit_code, logs, preview_url, and container metadata.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, preview_start, project_id, workspace_path, port)


def stop_preview(project_id: str) -> dict:
    """Explicitly stops and removes an active preview container."""
    return preview_stop(project_id)


async def run_build_and_repair_loop(
    project_id: str,
    workspace_path: str,
    repair_fn: Optional[Callable[[str, str], Union[bool, Awaitable[bool]]]] = None,
    port: Optional[int] = None,
) -> dict:
    """Executes the one-repair QA loop:
    1. Build once.
    2. If successful, start the preview and verify its health.
    3. If build or health check fails, send diagnostics to repair_fn (if provided).
    4. Exactly one repair attempt is permitted.
    5. Rebuild once after repair.
    6. If the second build fails, return final failure with useful logs.
    7. Never enters an infinite retry loop.
    """
    cumulative_logs = []

    # --- ATTEMPT 1 ---
    cumulative_logs.append("[QA Loop: Attempt 1] Initiating build...")
    build_1 = await build_project(project_id, workspace_path)
    cumulative_logs.append(build_1["logs"])

    if build_1["success"]:
        # Attempt preview start & healthcheck
        cumulative_logs.append("[QA Loop: Attempt 1] Build succeeded. Starting preview server...")
        preview_res = await start_preview(project_id, workspace_path, port=port)
        cumulative_logs.append(preview_res["logs"])

        if preview_res["success"]:
            cumulative_logs.append(f"[QA Loop] Preview verified healthy at {preview_res['preview_url']}")
            return {
                "success": True,
                "exit_code": 0,
                "logs": "\n\n".join(cumulative_logs),
                "preview_url": preview_res["preview_url"],
                "attempts": 1,
            }
        else:
            failure_reason = "Preview server failed health check"
            failed_logs = preview_res["logs"]
    else:
        failure_reason = f"Build failed with exit code {build_1['exit_code']}"
        failed_logs = build_1["logs"]

    # If no repair function provided, terminate with attempt 1 result
    if repair_fn is None:
        cumulative_logs.append(f"[QA Loop] {failure_reason}. No repair function registered.")
        return {
            "success": False,
            "exit_code": build_1.get("exit_code", 1),
            "logs": "\n\n".join(cumulative_logs),
            "preview_url": None,
            "attempts": 1,
        }

    # --- REPAIR DISPATCH (EXACTLY 1 ATTEMPT) ---
    cumulative_logs.append(f"[QA Loop: Repair] {failure_reason}. Invoking AI repair interface...")
    try:
        if inspect.iscoroutinefunction(repair_fn):
            repair_success = await repair_fn(project_id, failed_logs)
        else:
            repair_success = repair_fn(project_id, failed_logs)
    except Exception as exc:
        repair_success = False
        cumulative_logs.append(f"[QA Loop: Repair Exception] Repair invocation raised: {exc}")

    if not repair_success:
        cumulative_logs.append("[QA Loop: Repair Failed] AI repair was unable to resolve the issue.")
        return {
            "success": False,
            "exit_code": 1,
            "logs": "\n\n".join(cumulative_logs),
            "preview_url": None,
            "attempts": 1,
        }

    # --- ATTEMPT 2 (FINAL REBUILD) ---
    cumulative_logs.append("[QA Loop: Attempt 2] AI repair completed. Rebuilding project once...")
    build_2 = await build_project(project_id, workspace_path)
    cumulative_logs.append(build_2["logs"])

    if build_2["success"]:
        cumulative_logs.append("[QA Loop: Attempt 2] Rebuild succeeded! Starting preview server...")
        preview_res = await start_preview(project_id, workspace_path, port=port)
        cumulative_logs.append(preview_res["logs"])

        if preview_res["success"]:
            cumulative_logs.append(f"[QA Loop] Repaired preview verified healthy at {preview_res['preview_url']}")
            return {
                "success": True,
                "exit_code": 0,
                "logs": "\n\n".join(cumulative_logs),
                "preview_url": preview_res["preview_url"],
                "attempts": 2,
            }

    # Final failure after 1 repair attempt
    cumulative_logs.append("[QA Loop: Terminal Failure] Project failed again after one repair attempt.")
    return {
        "success": False,
        "exit_code": build_2.get("exit_code", 1),
        "logs": "\n\n".join(cumulative_logs),
        "preview_url": None,
        "attempts": 2,
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "success": False,
            "exit_code": 2,
            "logs": "Usage: py runner/runner.py <project-folder> [port]",
            "preview_url": None,
        }))
        return 2

    raw_path = sys.argv[1]
    port = None
    if len(sys.argv) > 2:
        try:
            port = int(sys.argv[2])
        except ValueError:
            print(json.dumps({
                "success": False,
                "exit_code": 1,
                "logs": "Port must be an integer between 1024 and 65535.",
                "preview_url": None,
            }))
            return 1
        if not (1024 <= port <= 65535):
            print(json.dumps({
                "success": False,
                "exit_code": 1,
                "logs": "Port must be between 1024 and 65535.",
                "preview_url": None,
            }))
            return 1

    # Validate path — any path-not-found or boundary error produces the user-friendly message
    try:
        validated_path = validate_workspace_path(raw_path)
    except ValueError:
        print(json.dumps({
            "success": False,
            "exit_code": 1,
            "logs": "Project folder or package.json not found.",
            "preview_url": None,
        }))
        return 1

    project_id = validated_path.name
    # Run build
    build_res = execute_build(workspace_path=str(validated_path), project_id=project_id)
    if not build_res.success:
        print(json.dumps({
            "success": False,
            "exit_code": build_res.exit_code,
            "logs": build_res.logs,
            "preview_url": None,
        }))
        return build_res.exit_code or 1

    # Run preview
    preview_res = preview_start(project_id=project_id, workspace_path=str(validated_path), port=port)
    output = {
        "success": preview_res["success"],
        "exit_code": preview_res["exit_code"],
        "logs": build_res.logs + "\n\n" + preview_res["logs"],
        "preview_url": preview_res["preview_url"],
    }
    print(json.dumps(output))
    return preview_res["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
