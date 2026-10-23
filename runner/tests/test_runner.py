import asyncio
import inspect
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runner.build import (
    BuildResultModel,
    execute_build,
    run_command,
    validate_project_id,
    validate_react_vite_project,
    validate_workspace_path,
)
from runner.preview import (
    find_available_port,
    is_port_in_use,
    start_preview,
    stop_preview,
)
from runner.runner import (
    BuildResult,
    build_project,
    build_project_sync,
    run_build_and_repair_loop,
)


def assert_true(cond, msg=""):
    if not cond:
        raise AssertionError(f"Assertion failed: {msg}")


def assert_equal(actual, expected, msg=""):
    if actual != expected:
        raise AssertionError(f"Expected {expected!r}, got {actual!r}. {msg}")


# ==============================================================================
# LIGHTWEIGHT DEPENDENCY-FREE MOCK FRAMEWORK (WORKS WITHOUT UNITTEST)
# ==============================================================================

class MockResult:
    def __init__(self, val):
        self.val = val
        self.status = 200

    def __getitem__(self, key):
        if isinstance(self.val, (dict, list, tuple)):
            return self.val[key]
        return getattr(self.val, key)

    def __iter__(self):
        return iter(self.val)

    def get(self, key, default=None):
        if isinstance(self.val, dict):
            return self.val.get(key, default)
        return getattr(self.val, key, default)

    def __bool__(self):
        return bool(self.val)

    def __eq__(self, other):
        return self.val == other

    def __await__(self):
        async def _coro():
            return self.val
        return _coro().__await__()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class MagicMock:
    def __init__(self, return_value=None, side_effect=None):
        self.return_value = return_value
        self.side_effect = side_effect
        self.call_count = 0
        self.calls = []
        self.status = 200

    def __call__(self, *args, **kwargs):
        self.call_count += 1
        self.calls.append((args, kwargs))
        if self.side_effect is not None:
            if callable(self.side_effect):
                val = self.side_effect(*args, **kwargs)
            elif isinstance(self.side_effect, Exception):
                raise self.side_effect
            elif hasattr(self.side_effect, "__iter__"):
                val = next(iter(self.side_effect))
            else:
                val = self.side_effect
        else:
            val = self.return_value
        return MockResult(val)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class patch:
    def __init__(self, target, return_value=None, side_effect=None):
        self.target = target
        self.return_value = return_value
        self.side_effect = side_effect
        self.orig = None
        self.module = None
        self.attr = None

    def __enter__(self):
        mod_name, attr = self.target.rsplit(".", 1)
        self.module = sys.modules[mod_name]
        self.attr = attr
        self.orig = getattr(self.module, attr)
        mock = MagicMock(return_value=self.return_value, side_effect=self.side_effect)
        setattr(self.module, attr, mock)
        return mock

    def __exit__(self, exc_type, exc_val, exc_tb):
        setattr(self.module, self.attr, self.orig)


# ==============================================================================
# 1. PATH TRAVERSAL AND WORKSPACE VALIDATION TESTS
# ==============================================================================

def test_missing_workspace():
    """Verifies that non-existent workspace paths are rejected."""
    bad_path = str(REPO_ROOT / "generated" / "non_existent_project_12345")
    res = execute_build(bad_path, project_id="test-proj")
    assert_equal(res.success, False, "Build should fail for non-existent workspace")
    assert_true("does not exist" in res.logs, f"Expected 'does not exist' in logs, got: {res.logs}")
    print("PASS: test_missing_workspace")


def test_unsafe_paths_and_path_traversal():
    """Verifies that directory traversal ('..') and out-of-boundary paths are blocked."""
    traversal_cases = [
        "../outside",
        "generated/../../outside",
        "../../etc/passwd",
        str(Path.home()),
    ]
    for case in traversal_cases:
        res = execute_build(case, project_id="test-proj")
        assert_equal(res.success, False, f"Build must reject traversal path: {case}")
        assert_true(
            "traversal" in res.logs.lower() or "escapes" in res.logs.lower() or "not exist" in res.logs.lower(),
            f"Expected traversal rejection in logs for {case}, got: {res.logs}"
        )
    print("PASS: test_unsafe_paths_and_path_traversal")


def test_missing_required_files():
    """Verifies that directories without package.json or without build scripts are rejected."""
    with tempfile.TemporaryDirectory(dir=REPO_ROOT / "generated") as tmpdir:
        # Case 1: Empty folder (no package.json)
        res = execute_build(tmpdir, project_id="test-empty")
        assert_equal(res.success, False)
        assert_true("Missing required 'package.json'" in res.logs)

        # Case 2: package.json missing 'build' script
        pkg = Path(tmpdir) / "package.json"
        pkg.write_text(json.dumps({"name": "test", "scripts": {"dev": "vite"}}), encoding="utf-8")
        res2 = execute_build(tmpdir, project_id="test-no-build")
        assert_equal(res2.success, False)
        assert_true("build' script" in res2.logs.lower())

        # Case 3: Missing React/Vite stack configuration
        pkg.write_text(json.dumps({
            "name": "test",
            "scripts": {"build": "webpack"},
            "dependencies": {"express": "4.0.0"}
        }), encoding="utf-8")
        res3 = execute_build(tmpdir, project_id="test-wrong-stack")
        assert_equal(res3.success, False)
        assert_true("react" in res3.logs.lower() and "vite" in res3.logs.lower())

    print("PASS: test_missing_required_files")


def test_invalid_project_id():
    """Verifies that malicious or invalid project IDs are blocked."""
    for bad_id in ["", "proj;rm -rf", "proj/../../hack", "a" * 70, "proj$name"]:
        try:
            validate_project_id(bad_id)
            raise AssertionError(f"Expected ValueError for project ID: {bad_id}")
        except ValueError:
            pass
    print("PASS: test_invalid_project_id")


# ==============================================================================
# 2. DETERMINISTIC DOCKER CALLS & DIAGNOSTICS TESTS (MOCKED)
# ==============================================================================

def test_successful_build_result_parsing():
    """Verifies that successful Docker build output is parsed into BuildResultModel."""
    sample_path = REPO_ROOT / "sandbox" / "sample-app"
    mock_docker_output = (0, "Successfully built abc123def456\nSuccessfully tagged hackmate-sample-app:local")

    with patch("runner.build.run_command", return_value=mock_docker_output):
        res = execute_build(str(sample_path), project_id="sample-app")
        assert_equal(res.success, True)
        assert_equal(res.exit_code, 0)
        assert_true("Successfully built" in res.logs)
        assert_equal(res.image_tag, "hackmate-sample-app:local")

    print("PASS: test_successful_build_result_parsing")


def test_failed_build_captured_diagnostics():
    """Verifies that Docker build errors capture detailed stderr diagnostics."""
    sample_path = REPO_ROOT / "sandbox" / "sample-app"
    mock_docker_error = (1, "ERROR: [build 6/6] RUN npm run build: TS2304: Cannot find name 'foo'")

    with patch("runner.build.run_command", return_value=mock_docker_error):
        res = execute_build(str(sample_path), project_id="sample-app")
        assert_equal(res.success, False)
        assert_equal(res.exit_code, 1)
        assert_true("TS2304" in res.logs)
        assert_true("BUILD FAILED" in res.logs)

    print("PASS: test_failed_build_captured_diagnostics")


def test_docker_command_timeout():
    """Verifies that command timeouts return exit code 124 and structured JSON."""
    sample_path = REPO_ROOT / "sandbox" / "sample-app"
    with patch("runner.build.run_command", return_value=(124, "Command 'docker build' timed out after 300 seconds.")):
        res = execute_build(str(sample_path), project_id="sample-app")
        assert_equal(res.success, False)
        assert_equal(res.exit_code, 124)
        assert_true("timed out" in res.logs)

    print("PASS: test_docker_command_timeout")


def test_docker_command_not_found():
    """Verifies graceful handling when docker executable is missing."""
    sample_path = REPO_ROOT / "sandbox" / "sample-app"
    with patch("runner.build.run_command", return_value=(127, "Executable not found: docker")):
        res = execute_build(str(sample_path), project_id="sample-app")
        assert_equal(res.success, False)
        assert_equal(res.exit_code, 127)
        assert_true("Executable not found" in res.logs)

    print("PASS: test_docker_command_not_found")


# ==============================================================================
# 3. PREVIEW LIFECYCLE & SECURITY CONFIGURATION TESTS
# ==============================================================================

def test_container_security_configuration():
    """Verifies that docker run args enforce all security flags and localhost binding."""
    sample_path = REPO_ROOT / "sandbox" / "sample-app"
    captured_args = []

    def mock_run(args, timeout=30):
        captured_args.append(args)
        return (0, "container-id-123")

    with patch("runner.preview.run_command", side_effect=mock_run), \
         patch("urllib.request.urlopen") as mock_url:
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_url.return_value = mock_resp

        res = start_preview(project_id="sample-app", workspace_path=str(sample_path), port=8089)
        assert_equal(res["success"], True)

    run_cmd = next(cmd for cmd in captured_args if "run" in cmd)
    assert_true("--security-opt=no-new-privileges" in run_cmd, "Must include no-new-privileges")
    assert_true("--memory=512m" in run_cmd, "Must include memory limit 512m")
    assert_true("--cpus=1" in run_cmd, "Must include CPU limit 1")
    assert_true("--pids-limit=128" in run_cmd, "Must include pids-limit 128")
    assert_true("--restart=no" in run_cmd, "Must include restart=no")
    assert_true("-p" in run_cmd, "Must map port")
    assert_true("127.0.0.1:8089:80" in run_cmd, "Must bind strictly to loopback 127.0.0.1:8089:80")

    print("PASS: test_container_security_configuration")


def test_port_conflicts_and_detection():
    """Verifies that occupied ports are detected and alternative ports are selected."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as occupied_sock:
        occupied_sock.bind(("127.0.0.1", 0))
        occupied_port = occupied_sock.getsockname()[1]

        # 1. is_port_in_use should detect it
        assert_true(is_port_in_use(occupied_port), f"Port {occupied_port} should be reported as in use")

        # 2. start_preview with explicit occupied port should reject with Port Collision
        sample_path = REPO_ROOT / "sandbox" / "sample-app"
        res = start_preview("sample-app", str(sample_path), port=occupied_port)
        assert_equal(res["success"], False)
        assert_true("Port Collision" in res["logs"], f"Expected Port Collision in logs, got: {res['logs']}")

        # 3. find_available_port should safely find an unbound port
        free_port = find_available_port(start_port=8081, max_port=8200)
        assert_true(free_port != occupied_port, "Must find an unoccupied port")

    print("PASS: test_port_conflicts_and_detection")


def test_failed_http_health_check_and_cleanup():
    """Verifies that a failing healthcheck captures container logs and deletes the container."""
    sample_path = REPO_ROOT / "sandbox" / "sample-app"
    rm_calls = []

    def mock_run(args, timeout=30):
        if "rm" in args:
            rm_calls.append(args)
        return (0, "logs-or-id")

    with patch("runner.preview.run_command", side_effect=mock_run), \
         patch("urllib.request.urlopen", side_effect=OSError("Connection refused")):
        res = start_preview(
            project_id="sample-app",
            workspace_path=str(sample_path),
            port=8092,
            health_timeout=2,
        )
        assert_equal(res["success"], False)
        assert_true("health check failed" in res["logs"].lower())
        assert_true(len(rm_calls) >= 2, "Must call docker rm to clean up failed container")

    print("PASS: test_failed_http_health_check_and_cleanup")


def test_resource_cleanup():
    """Verifies that stop_preview removes the designated container only."""
    with patch("runner.preview.run_command", return_value=(0, "hackmate-preview-my-app")):
        res = stop_preview("my-app")
        assert_equal(res["success"], True)
        assert_equal(res["container_name"], "hackmate-preview-my-app")
    print("PASS: test_resource_cleanup")


# ==============================================================================
# 4. ONE-REPAIR QA LOOP TESTS
# ==============================================================================

def test_one_repair_qa_loop_success_on_attempt_1():
    """Verifies that a clean build succeeds immediately without triggering repair."""
    repair_mock = MagicMock(return_value=True)

    with patch("runner.runner.build_project", return_value={"success": True, "exit_code": 0, "logs": "Build OK"}), \
         patch("runner.runner.start_preview", return_value={"success": True, "exit_code": 0, "logs": "Preview OK", "preview_url": "http://127.0.0.1:8081/"}):

        res = asyncio.run(run_build_and_repair_loop("proj-1", "./sandbox/sample-app", repair_fn=repair_mock))
        assert_equal(res["success"], True)
        assert_equal(res["attempts"], 1)
        assert_equal(repair_mock.call_count, 0, "Repair should not be invoked on successful first build")

    print("PASS: test_one_repair_qa_loop_success_on_attempt_1")


def test_one_repair_qa_loop_repair_and_rebuild_success():
    """Verifies that build failure triggers repair once, followed by a successful rebuild."""
    repair_mock = MagicMock(return_value=True)
    build_results = [
        {"success": False, "exit_code": 1, "logs": "Syntax error in App.jsx"},
        {"success": True, "exit_code": 0, "logs": "Rebuild OK"},
    ]

    def mock_build(project_id, path):
        return build_results.pop(0)

    with patch("runner.runner.build_project", side_effect=mock_build), \
         patch("runner.runner.start_preview", return_value={"success": True, "exit_code": 0, "logs": "Preview OK", "preview_url": "http://127.0.0.1:8081/"}):

        res = asyncio.run(run_build_and_repair_loop("proj-2", "./sandbox/sample-app", repair_fn=repair_mock))
        assert_equal(res["success"], True)
        assert_equal(res["attempts"], 2)
        assert_equal(repair_mock.call_count, 1, "Repair must be invoked exactly once")
        assert_true("Syntax error" in res["logs"])
        assert_true("Rebuild succeeded" in res["logs"])

    print("PASS: test_one_repair_qa_loop_repair_and_rebuild_success")


def test_one_repair_qa_loop_terminal_failure_after_second_build():
    """Verifies that if rebuild fails after repair, loop terminates with failure and never loops infinitely."""
    repair_mock = MagicMock(return_value=True)
    build_results = [
        {"success": False, "exit_code": 1, "logs": "Syntax error 1"},
        {"success": False, "exit_code": 1, "logs": "Syntax error 2 (still broken)"},
        {"success": True, "exit_code": 0, "logs": "Should never reach attempt 3"},
    ]

    def mock_build(project_id, path):
        return build_results.pop(0)

    with patch("runner.runner.build_project", side_effect=mock_build), \
         patch("runner.runner.start_preview", return_value={"success": True, "exit_code": 0, "logs": "Preview OK"}):

        res = asyncio.run(run_build_and_repair_loop("proj-3", "./sandbox/sample-app", repair_fn=repair_mock))
        assert_equal(res["success"], False)
        assert_equal(res["attempts"], 2)
        assert_equal(repair_mock.call_count, 1, "Repair must not be called more than once")
        assert_true("Terminal Failure" in res["logs"])

    print("PASS: test_one_repair_qa_loop_terminal_failure_after_second_build")


# ==============================================================================
# 5. REAL DOCKER E2E TEST (RUN IF DOCKER DAEMON REACHABLE)
# ==============================================================================

def is_docker_daemon_reachable():
    try:
        proc = subprocess.run(["docker", "version"], capture_output=True, text=True, timeout=5)
        return proc.returncode == 0
    except Exception:
        return False


def test_real_docker_e2e_preview():
    """Executes a real Docker build, container launch, localhost healthcheck, and teardown."""
    if not is_docker_daemon_reachable():
        print("SKIP: Real Docker daemon is not reachable in this process. Skipping real E2E test.")
        return

    sample_path = str(REPO_ROOT / "sandbox" / "sample-app")
    project_id = "sample-app"
    test_port = 8095

    # Ensure pre-cleanup
    stop_preview(project_id)

    try:
        print(f"\n[Real Docker E2E] Executing build on {sample_path}...")
        build_res = execute_build(workspace_path=sample_path, project_id=project_id)
        assert_equal(build_res.success, True, f"Real Docker build failed: {build_res.logs}")
        assert_equal(build_res.exit_code, 0)
        print("PASS: Real Docker build completed successfully.")

        print(f"[Real Docker E2E] Starting preview container on port {test_port}...")
        preview_res = start_preview(project_id=project_id, workspace_path=sample_path, port=test_port)
        assert_equal(preview_res["success"], True, f"Real preview failed: {preview_res['logs']}")
        assert_equal(preview_res["preview_url"], f"http://127.0.0.1:{test_port}/")
        print(f"PASS: Preview server is healthy at {preview_res['preview_url']}")

        # Verify container configuration directly from Docker daemon
        inspect_proc = subprocess.run(
            ["docker", "inspect", f"hackmate-preview-{project_id}"],
            capture_output=True,
            text=True,
            check=True,
        )
        inspect_data = json.loads(inspect_proc.stdout)[0]

        # Port binding check (HostIp MUST be 127.0.0.1)
        port_binds = inspect_data["NetworkSettings"]["Ports"]["80/tcp"]
        assert_equal(port_binds[0]["HostIp"], "127.0.0.1", "Port must bind strictly to 127.0.0.1")
        assert_equal(port_binds[0]["HostPort"], str(test_port))
        print("PASS: Localhost-only binding verified via docker inspect.")

        # Resource limits check
        assert_equal(inspect_data["HostConfig"]["Memory"], 536870912, "Memory must be 512MB")
        assert_equal(inspect_data["HostConfig"]["PidsLimit"], 128, "PID limit must be 128")
        assert_equal(inspect_data["HostConfig"]["NanoCpus"], 1000000000, "CPU limit must be 1.0 CPU")
        print("PASS: Resource limits (Memory: 512MB, CPU: 1.0, PIDs: 128) verified.")

    finally:
        # Teardown
        stop_res = stop_preview(project_id)
        assert_equal(stop_res["success"], True, "Failed to clean up preview container")
        print("PASS: Real Docker container stopped and cleaned up.")

    print("PASS: test_real_docker_e2e_preview")


# ==============================================================================
# MAIN TEST DISPATCHER
# ==============================================================================

def main():
    print("=" * 60)
    print("HackMate Person 4: Deterministic Runner Unit & Security Tests")
    print("=" * 60)

    # 1. Validation & Traversal
    test_missing_workspace()
    test_unsafe_paths_and_path_traversal()
    test_missing_required_files()
    test_invalid_project_id()

    # 2. Mocked Docker Calls & Captured Diagnostics
    test_successful_build_result_parsing()
    test_failed_build_captured_diagnostics()
    test_docker_command_timeout()
    test_docker_command_not_found()

    # 3. Preview Lifecycle & Security
    test_container_security_configuration()
    test_port_conflicts_and_detection()
    test_failed_http_health_check_and_cleanup()
    test_resource_cleanup()

    # 4. QA One-Repair Loop
    test_one_repair_qa_loop_success_on_attempt_1()
    test_one_repair_qa_loop_repair_and_rebuild_success()
    test_one_repair_qa_loop_terminal_failure_after_second_build()

    print("\n" + "=" * 60)
    print("Executing Real Docker End-to-End Test (if Daemon Available)")
    print("=" * 60)
    test_real_docker_e2e_preview()

    print("\n" + "=" * 60)
    print("ALL RUNNER TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    main()
