import asyncio
import os
import shutil
import sys
from pathlib import Path
from typing import Callable, Coroutine, Optional, Tuple
from app.config import settings
from app.core.errors import RunnerUnavailableError, BuildExecutionError
from app.core.logging import logger


class RunnerService:
    """
    Manages sandboxed build execution.
    Primary target: Hardened Docker container with resource caps and dropped privileges.
    Development fallback: Local Node.js subprocess only when explicitly enabled via configuration.
    """

    async def check_docker_available(self) -> Tuple[bool, str]:
        """Checks if the Docker CLI and daemon are responsive."""
        docker_cmd = shutil.which("docker")
        if not docker_cmd:
            return False, "Docker CLI is not installed or not in PATH."

        try:
            process = await asyncio.create_subprocess_exec(
                docker_cmd, "info",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=4.0)
            if process.returncode == 0:
                return True, "Docker daemon is running and responsive."
            else:
                err_msg = stderr.decode("utf-8", errors="ignore").strip()
                return False, f"Docker daemon is not reachable: {err_msg[:120]}"
        except asyncio.TimeoutError:
            return False, "Docker daemon connection timed out."
        except Exception as e:
            return False, f"Failed to probe Docker daemon: {str(e)}"

    async def execute_build(
        self,
        project_id: str,
        workspace_path: Path,
        on_log_chunk: Optional[Callable[[str, str], Coroutine]] = None,
        cancellation_token: Optional[asyncio.Event] = None,
    ) -> Tuple[bool, int, str]:
        """
        Executes `npm install` and `npm run build` in a sandboxed environment.
        Returns: (success: bool, exit_code: int, error_summary: str)
        """
        docker_ok, docker_reason = await self.check_docker_available()

        if docker_ok and settings.RUNNER_TYPE == "docker":
            return await self._run_docker_build(
                project_id, workspace_path, on_log_chunk, cancellation_token
            )

        # Docker is unavailable or RUNNER_TYPE is not docker
        if settings.is_production:
            raise RunnerUnavailableError(
                f"Docker is mandatory in production, but is unavailable: {docker_reason}. "
                "Direct host execution is strictly forbidden."
            )

        if not settings.ENABLE_LOCAL_DEV_RUNNER:
            raise RunnerUnavailableError(
                f"Docker daemon is not running ({docker_reason}). "
                "Direct host execution is disabled by default for safety. "
                "Start Docker Desktop or explicitly set ENABLE_LOCAL_DEV_RUNNER=true in backend/.env for local development."
            )

        logger.warning(f"Using development-only local runner for project {project_id}.")
        return await self._run_local_dev_build(
            project_id, workspace_path, on_log_chunk, cancellation_token
        )

    async def _run_docker_build(
        self,
        project_id: str,
        workspace_path: Path,
        on_log_chunk: Optional[Callable[[str, str], Coroutine]],
        cancellation_token: Optional[asyncio.Event],
    ) -> Tuple[bool, int, str]:
        """Runs the build inside an unprivileged Docker container with resource caps."""
        container_name = f"hackmate-build-{project_id}"
        norm_workspace = workspace_path.as_posix()

        # Hardened docker run arguments
        cmd = [
            "docker", "run", "--rm",
            "--name", container_name,
            "-v", f"{norm_workspace}:/app",
            "-w", "/app",
            "--user", "1001:1001",
            "--cpus", "1.5",
            "--memory", "1024m",
            "--pids-limit", "100",
            "--security-opt", "no-new-privileges:true",
            settings.DOCKER_IMAGE_NAME,
            "sh", "-c", "npm install --prefer-offline --no-audit && npm run build"
        ]

        return await self._spawn_process(
            cmd, workspace_path, on_log_chunk, cancellation_token, kill_container_name=container_name
        )

    async def _run_local_dev_build(
        self,
        project_id: str,
        workspace_path: Path,
        on_log_chunk: Optional[Callable[[str, str], Coroutine]],
        cancellation_token: Optional[asyncio.Event],
    ) -> Tuple[bool, int, str]:
        """Development-only fallback runner using local npm executable."""
        npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"

        # Check npm exists
        if not shutil.which(npm_cmd):
            raise RunnerUnavailableError(f"Local Node/npm executable '{npm_cmd}' was not found in PATH.")

        # Step 1: npm install
        install_cmd = [npm_cmd, "install", "--no-audit"]
        ok, code, err = await self._spawn_process(
            install_cmd, workspace_path, on_log_chunk, cancellation_token
        )
        if not ok:
            return False, code, f"Dependency installation failed: {err}"

        # Step 2: npm run build
        build_cmd = [npm_cmd, "run", "build"]
        return await self._spawn_process(
            build_cmd, workspace_path, on_log_chunk, cancellation_token
        )

    async def _spawn_process(
        self,
        cmd: list,
        cwd: Path,
        on_log_chunk: Optional[Callable[[str, str], Coroutine]],
        cancellation_token: Optional[asyncio.Event],
        kill_container_name: Optional[str] = None,
    ) -> Tuple[bool, int, str]:
        """Spawns an async process with real-time log streaming, timeout, and cancellation."""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except Exception as e:
            raise BuildExecutionError(f"Failed to spawn build process: {str(e)}")

        accumulated_stderr = []
        accumulated_all = []

        async def stream_reader(stream, stream_name: str):
            while True:
                line = await stream.readline()
                if not line:
                    break
                decoded = line.decode("utf-8", errors="replace")
                accumulated_all.append(decoded)
                if stream_name == "stderr":
                    accumulated_stderr.append(decoded)
                if on_log_chunk:
                    await on_log_chunk(stream_name, decoded)

        read_tasks = asyncio.gather(
            stream_reader(process.stdout, "stdout"),
            stream_reader(process.stderr, "stderr"),
        )

        try:
            # Watch for process completion or cancellation
            done_or_timeout = asyncio.ensure_future(
                asyncio.wait_for(
                    asyncio.gather(process.wait(), read_tasks),
                    timeout=float(settings.BUILD_TIMEOUT_SECONDS)
                )
            )

            if cancellation_token:
                cancel_watcher = asyncio.ensure_future(cancellation_token.wait())
                done, pending = await asyncio.wait(
                    [done_or_timeout, cancel_watcher],
                    return_when=asyncio.FIRST_COMPLETED
                )

                if cancel_watcher in done:
                    # User cancelled
                    process.kill()
                    if kill_container_name:
                        await self._kill_docker_container(kill_container_name)
                    return False, -1, "Build was cancelled by user."

            await done_or_timeout

        except asyncio.TimeoutError:
            process.kill()
            if kill_container_name:
                await self._kill_docker_container(kill_container_name)
            return False, -2, f"Build timed out after {settings.BUILD_TIMEOUT_SECONDS} seconds."

        exit_code = process.returncode or 0
        if exit_code != 0:
            error_summary = "".join(accumulated_stderr)[-2000:] if accumulated_stderr else "".join(accumulated_all)[-2000:]
        else:
            error_summary = ""
        return (exit_code == 0), exit_code, error_summary

    async def _kill_docker_container(self, container_name: str):
        try:
            kill_proc = await asyncio.create_subprocess_exec(
                "docker", "rm", "-f", container_name,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await kill_proc.wait()
        except Exception:
            pass


runner_service = RunnerService()
