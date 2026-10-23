import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


DOCKERFILE = Path(__file__).with_name("runner.Dockerfile")


def run_command(args, timeout=300):
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return result.returncode, (result.stdout + result.stderr).strip()


def main():
    if len(sys.argv) < 2:
        print("Usage: py sandbox/runner.py <project-folder> [port]")
        return 2

    project = Path(sys.argv[1]).resolve()
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8081

    if not project.is_dir() or not (project / "package.json").is_file():
        print(json.dumps({
            "success": False,
            "exit_code": 1,
            "logs": "Project folder or package.json not found.",
            "preview_url": None,
        }))
        return 1

    if not DOCKERFILE.is_file():
        print("Runner Dockerfile not found: " + str(DOCKERFILE))
        return 1

    if not 1024 <= port <= 65535:
        print("Port must be between 1024 and 65535.")
        return 1

    project_id = re.sub(r"[^a-z0-9-]", "-", project.name.lower()).strip("-")
    if not project_id:
        project_id = "app"

    container = f"hackmate-preview-{project_id}"
    image = f"hackmate-{project_id}:local"
    url = f"http://127.0.0.1:{port}/"
    logs = []

    ignore_file = project / ".dockerignore"
    if not ignore_file.exists():
        ignore_file.write_text(
            "node_modules\ndist\n.git\n.env\n.env.*\n",
            encoding="utf-8",
        )

    try:
        run_command(["docker", "rm", "-f", container], timeout=20)

        code, output = run_command([
            "docker", "build",
            "-f", str(DOCKERFILE),
            "-t", image,
            str(project),
        ])
        logs.append("BUILD:\n" + output)

        if code != 0:
            print(json.dumps({
                "success": False,
                "exit_code": code,
                "logs": "\n\n".join(logs),
                "preview_url": None,
            }))
            return code or 1

        code, output = run_command([
            "docker", "run", "-d",
            "--name", container,
            "--restart=no",
            "--memory=512m",
            "--cpus=1",
            "--pids-limit=128",
            "--security-opt=no-new-privileges",
            "-p", f"127.0.0.1:{port}:80",
            image,
        ], timeout=30)
        logs.append("START:\n" + output)

        if code != 0:
            print(json.dumps({
                "success": False,
                "exit_code": code,
                "logs": "\n\n".join(logs),
                "preview_url": None,
            }))
            return code or 1

        for _ in range(20):
            try:
                request = urllib.request.urlopen(url, timeout=2)
                with request:
                    if request.status == 200:
                        logs.append("HTTP health check passed: 200")
                        print(json.dumps({
                            "success": True,
                            "exit_code": 0,
                            "logs": "\n\n".join(logs),
                            "preview_url": url,
                        }))
                        return 0
            except (urllib.error.URLError, TimeoutError, OSError):
                time.sleep(1)

        _, container_logs = run_command(
            ["docker", "logs", container], timeout=20
        )
        logs.append("HTTP health check failed.")
        logs.append("CONTAINER LOGS:\n" + container_logs)

        print(json.dumps({
            "success": False,
            "exit_code": 1,
            "logs": "\n\n".join(logs),
            "preview_url": None,
        }))
        return 1

    except subprocess.TimeoutExpired:
        print(json.dumps({
            "success": False,
            "exit_code": 124,
            "logs": "\n\n".join(logs) + "\nDocker command timed out.",
            "preview_url": None,
        }))
        return 124


if __name__ == "__main__":
    raise SystemExit(main())
