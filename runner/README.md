# HackMate Runner & QA Sandbox

The **HackMate Runner** provides an isolated, hardened execution environment for building, validating, and previewing generated React + Vite applications.

---

## 1. Security Architecture & Boundary

Generated code is **never** executed directly on the host system. All builds and live previews run strictly inside dedicated Docker containers with deep defense-in-depth protections:

1. **Localhost-Only Loopback Binding:** Previews bind strictly to `127.0.0.1:{port}:80` (loopback only), preventing exposure to LAN or external network interfaces.
2. **Resource Constraints:**
   - **Memory Limit:** Capped at `512MB` (`--memory=512m`) to prevent out-of-memory crashes on the host.
   - **CPU Limit:** Capped at `1.0` CPU core (`--cpus=1`) to prevent CPU exhaustion.
   - **Process Limit:** Capped at `128` processes (`--pids-limit=128`) to block fork-bombs.
   - **Restart Policy:** `--restart=no` prevents crash-loop thrashing.
3. **Privilege Escalation Protection:** Containers run with `--security-opt=no-new-privileges` to prevent privilege escalation.
4. **No Docker Socket Mounting:** The host Docker socket (`/var/run/docker.sock` or `//./pipe/docker_engine`) is **never** mounted into application containers.
5. **Secret & Host Isolation:** Automated `.dockerignore` generation ensures host `.env`, `.git`, `node_modules`, and sensitive credentials never leak into container build contexts.
6. **Path Traversal Shield:** All workspace paths are validated to ensure they cannot escape approved directories (`./generated`, `./sandbox`, `./workspace`). Any paths containing `..` or pointing outside boundaries are immediately rejected.
7. **Windows Docker Desktop Note:** Container isolation on Windows utilizes WSL2/Hyper-V virtualization. While resource caps are strictly enforced by the Docker daemon, network isolation depends on the local Docker Desktop engine being active.

---

## 2. Prerequisites & Setup

### Requirements
- **Docker Desktop for Windows:** Must be running with the Linux container engine (WSL2 backend recommended).
- **Python 3.10+** (or Python runtime accessible via PowerShell).

---

## 3. How to Run the Runner

### Building and Starting a Live Preview

From PowerShell in the repository root:

```powershell
# Set Python path (if using MySQL Python or custom installation)
$env:PYTHONHOME = "C:\Program Files\MySQL\MySQL Workbench 8.0 CE\python"

# Run preview on a project folder (specifying optional port 8081)
& "C:\Program Files\MySQL\MySQL Workbench 8.0 CE\python.exe" runner/runner.py sandbox/sample-app 8081
```

*(You can also invoke via `sandbox/runner.py`, which delegates seamlessly to the authoritative runner).*

### Expected Output Format

The runner consistently outputs structured JSON conforming to the HackMate `BuildResult` contract:

```json
{
  "success": true,
  "exit_code": 0,
  "logs": "BUILD SUCCEEDED:\n...\nSTART CONTAINER (hackmate-preview-sample-app):\n...\nHTTP health check passed: 200 OK from http://127.0.0.1:8081/",
  "preview_url": "http://127.0.0.1:8081/"
}
```

---

## 4. Stopping and Cleaning Up Previews

To stop an active preview container:

```powershell
docker rm -f hackmate-preview-sample-app
```

Or programmatically in Python:
```python
from runner.runner import stop_preview

stop_preview("sample-app")
```

---

## 5. Automated Tests

Run the full deterministic unit test and security test suite:

```powershell
# Run the complete test suite
$env:PYTHONHOME = "C:\Program Files\MySQL\MySQL Workbench 8.0 CE\python"
& "C:\Program Files\MySQL\MySQL Workbench 8.0 CE\python.exe" runner/tests/test_runner.py
```

Or run the convenient PowerShell test script:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/test-sandbox.ps1
```

### What the Test Suite Covers:
- **Path Traversal Rejection:** Verifies `..` and external paths are rejected.
- **Missing Required Files:** Verifies missing `package.json` or build scripts are caught.
- **Stack Validation:** Enforces React + Vite stack rules.
- **Mocked Docker Diagnostics:** Tests error capture, timeouts (code 124), and missing CLI (code 127).
- **Container Security Configuration:** Asserts loopback binding, memory (512M), CPU (1.0), and PID caps (128).
- **Port Conflict Handling:** Tests automatic collision avoidance.
- **One-Repair QA Loop:** Tests that failing builds trigger AI repair once, rebuild once, and strictly terminate without infinite retries.
- **Real Docker E2E:** Executes actual container build, run, and HTTP 200 health check if Docker Desktop is reachable.

---

## 6. One-Repair QA Loop & Team Coordination

The runner provides `run_build_and_repair_loop(project_id, workspace_path, repair_fn=...)`.

### Workflow:
1. **Build 1:** Builds the React + Vite bundle in Docker.
2. **Preview 1:** Starts container and verifies HTTP 200. If healthy, returns immediately.
3. **Repair Dispatch:** If build or preview fails, passes error logs to `repair_fn(project_id, error_logs)`.
4. **Build 2:** If repair succeeds, rebuilds once.
5. **Terminal Evaluation:** If second build fails, returns final failure. Retries are strictly capped at 1.

### Team Interface Integration:
- **Person 1 (Frontend):** Mounts `preview_url` (e.g. `http://127.0.0.1:8081/`) into the preview iframe.
- **Person 2 (Backend):** Can call `await build_project(project_id, workspace_path)` or `await run_build_and_repair_loop(...)` in `ProjectPipeline`.
- **Person 3 (AI Engineering):** When the AI repair agent is implemented in `ai/`, pass its callable as `repair_fn` to complete autonomous self-healing.
