import json
import re
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional, Tuple

from runner.build import (
    DEFAULT_TIMEOUT,
    execute_build,
    run_command,
    validate_project_id,
    validate_workspace_path,
)


HEALTH_CHECK_RETRIES = 25
HEALTH_CHECK_DELAY = 1.0


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Checks if a TCP port on host is already bound or in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
            return False
        except OSError:
            return True


def find_available_port(start_port: int = 8081, max_port: int = 8200) -> int:
    """Finds an unbound TCP port on 127.0.0.1 within the given range."""
    for port in range(start_port, max_port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No free port available on 127.0.0.1 between {start_port} and {max_port}.")


def start_preview(
    project_id: str,
    workspace_path: str,
    port: Optional[int] = None,
    health_timeout: int = 30,
) -> dict:
    """Spins up an isolated Nginx container for the project and verifies readiness via HTTP healthcheck."""
    try:
        clean_id = validate_project_id(project_id)
        safe_path = validate_workspace_path(workspace_path)
    except ValueError as err:
        return {
            "success": False,
            "exit_code": 1,
            "logs": f"[Preview Error] {err}",
            "preview_url": None,
        }

    container_name = f"hackmate-preview-{clean_id.lower()}"
    image_tag = f"hackmate-{clean_id.lower()}:local"

    # 1. Port selection and collision avoidance
    if port is None:
        try:
            port = find_available_port()
        except RuntimeError as err:
            return {
                "success": False,
                "exit_code": 1,
                "logs": f"[Port Error] {err}",
                "preview_url": None,
            }
    else:
        if not 1024 <= port <= 65535:
            return {
                "success": False,
                "exit_code": 1,
                "logs": f"[Port Error] Port {port} is out of bounds (1024-65535).",
                "preview_url": None,
            }
        if is_port_in_use(port):
            return {
                "success": False,
                "exit_code": 1,
                "logs": f"[Port Collision] Port {port} on 127.0.0.1 is already in use by another service.",
                "preview_url": None,
            }

    url = f"http://127.0.0.1:{port}/"
    logs = []

    # 2. Clean up any previous container for this project only
    run_command(["docker", "rm", "-f", container_name], timeout=15)

    # 3. Start container with strict security isolation & resource caps
    run_args = [
        "docker", "run", "-d",
        "--name", container_name,
        "--restart=no",
        "--memory=512m",
        "--cpus=1",
        "--pids-limit=128",
        "--security-opt=no-new-privileges",
        "-p", f"127.0.0.1:{port}:80",
        image_tag,
    ]

    code, output = run_command(run_args, timeout=30)
    logs.append(f"START CONTAINER ({container_name}):\n{output}")

    if code != 0:
        return {
            "success": False,
            "exit_code": code,
            "logs": "\n\n".join(logs),
            "preview_url": None,
            "container_name": container_name,
        }

    # 4. HTTP Healthcheck loop: verify HTTP 200 before returning preview URL
    deadline = time.time() + health_timeout
    healthy = False

    while time.time() < deadline:
        try:
            req = urllib.request.urlopen(url, timeout=2)
            with req:
                if req.status == 200:
                    healthy = True
                    logs.append(f"HTTP health check passed: 200 OK from {url}")
                    break
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(HEALTH_CHECK_DELAY)

    if healthy:
        return {
            "success": True,
            "exit_code": 0,
            "logs": "\n\n".join(logs),
            "preview_url": url,
            "container_name": container_name,
            "port": port,
        }

    # 5. Handle failed start: capture container stderr/logs and clean up
    _, container_logs = run_command(["docker", "logs", container_name], timeout=10)
    run_command(["docker", "rm", "-f", container_name], timeout=10)

    logs.append(f"HTTP health check failed after {health_timeout}s.")
    logs.append(f"CONTAINER LOGS:\n{container_logs}")

    return {
        "success": False,
        "exit_code": 1,
        "logs": "\n\n".join(logs),
        "preview_url": None,
        "container_name": container_name,
    }


def stop_preview(project_id: str) -> dict:
    """Stops and removes the preview container for a project."""
    try:
        clean_id = validate_project_id(project_id)
    except ValueError as err:
        return {"success": False, "exit_code": 1, "logs": str(err)}

    container_name = f"hackmate-preview-{clean_id.lower()}"
    code, output = run_command(["docker", "rm", "-f", container_name], timeout=15)
    return {
        "success": code == 0,
        "exit_code": code,
        "logs": output,
        "container_name": container_name,
    }
