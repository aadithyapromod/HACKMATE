import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RUNNER_SCRIPT = REPO_ROOT / "sandbox" / "runner.py"
SAMPLE_APP = REPO_ROOT / "sandbox" / "sample-app"


def run_runner(*args):
    """Executes sandbox/runner.py using the current python executable."""
    cmd = [sys.executable, str(RUNNER_SCRIPT), *args]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.returncode, res.stdout, res.stderr


def is_docker_available():
    try:
        res = subprocess.run(["docker", "version"], capture_output=True, text=True, timeout=5)
        return res.returncode == 0
    except Exception:
        return False


def test_missing_arguments_returns_json():
    code, stdout, stderr = run_runner()
    assert code == 2, f"Expected code 2, got {code}"
    data = json.loads(stdout.strip())
    assert not data["success"], "Expected success to be False"
    assert data["exit_code"] == 2, f"Expected exit_code 2, got {data['exit_code']}"
    assert "Usage:" in data["logs"], f"Expected 'Usage:' in logs, got {data['logs']}"
    assert data["preview_url"] is None, "Expected preview_url to be None"
    print("PASS: test_missing_arguments_returns_json")


def test_nonexistent_directory_returns_json():
    code, stdout, stderr = run_runner("non_existent_folder_xyz")
    assert code == 1, f"Expected code 1, got {code}"
    data = json.loads(stdout.strip())
    assert not data["success"], "Expected success to be False"
    assert data["exit_code"] == 1, f"Expected exit_code 1, got {data['exit_code']}"
    assert "Project folder or package.json not found" in data["logs"]
    print("PASS: test_nonexistent_directory_returns_json")


def test_missing_package_json_returns_json():
    with tempfile.TemporaryDirectory() as tmpdir:
        code, stdout, stderr = run_runner(tmpdir)
        assert code == 1, f"Expected code 1, got {code}"
        data = json.loads(stdout.strip())
        assert not data["success"], "Expected success to be False"
        assert "Project folder or package.json not found" in data["logs"]
    print("PASS: test_missing_package_json_returns_json")


def test_invalid_port_string_returns_json():
    code, stdout, stderr = run_runner(str(SAMPLE_APP), "not-a-port")
    assert code == 1, f"Expected code 1, got {code}"
    data = json.loads(stdout.strip())
    assert not data["success"], "Expected success to be False"
    assert "Port must be an integer" in data["logs"]
    print("PASS: test_invalid_port_string_returns_json")


def test_port_out_of_range_returns_json():
    for bad_port in ["80", "80000"]:
        code, stdout, stderr = run_runner(str(SAMPLE_APP), bad_port)
        assert code == 1, f"Expected code 1 for port {bad_port}, got {code}"
        data = json.loads(stdout.strip())
        assert not data["success"], f"Expected success False for port {bad_port}"
        assert "Port must be between 1024 and 65535" in data["logs"]
    print("PASS: test_port_out_of_range_returns_json")


def test_sample_app_docker_preview_end_to_end():
    if not is_docker_available():
        print("SKIP: Docker daemon is not reachable in this process. Skipping Docker E2E test.")
        return

    port = 8099
    container_name = "hackmate-preview-sample-app"

    # Pre-clean
    subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)

    try:
        print(f"Running sandbox/runner.py on {SAMPLE_APP} at port {port}...")
        code, stdout, stderr = run_runner(str(SAMPLE_APP), str(port))
        assert code == 0, f"Runner failed with code {code}.\nStdout: {stdout}\nStderr: {stderr}"

        data = json.loads(stdout.strip())
        assert data["success"] is True, f"Expected success True, got {data}"
        assert data["exit_code"] == 0, f"Expected exit_code 0, got {data}"
        assert data["preview_url"] == f"http://127.0.0.1:{port}/"

        # 1. HTTP 200 health check
        req = urllib.request.urlopen(data["preview_url"], timeout=5)
        with req:
            assert req.status == 200, f"Expected HTTP 200, got {req.status}"
            body = req.read().decode("utf-8")
            assert "<title>" in body or "html" in body.lower(), "HTML title tag missing"
        print(f"PASS: HTTP 200 verification on {data['preview_url']}")

        # 2. Inspect Docker container for localhost-only binding and resource limits
        inspect_res = subprocess.run(
            ["docker", "inspect", container_name],
            capture_output=True,
            text=True,
            check=True,
        )
        inspect_data = json.loads(inspect_res.stdout)[0]

        # Port binding check (HostIp MUST be 127.0.0.1)
        port_bindings = inspect_data["NetworkSettings"]["Ports"]["80/tcp"]
        assert port_bindings is not None, "Port 80/tcp not bound"
        assert port_bindings[0]["HostIp"] == "127.0.0.1", f"HostIp is {port_bindings[0]['HostIp']}, expected 127.0.0.1"
        assert port_bindings[0]["HostPort"] == str(port), f"HostPort is {port_bindings[0]['HostPort']}, expected {port}"
        print(f"PASS: Localhost binding verified (127.0.0.1:{port})")

        # Memory limit check (512MB = 536870912 bytes)
        mem = inspect_data["HostConfig"]["Memory"]
        assert mem == 536870912, f"Expected memory 536870912, got {mem}"
        print(f"PASS: Memory limit verified ({mem} bytes / 512 MB)")

        # CPU limit check (1 CPU = 1000000000 NanoCpus)
        nanocpus = inspect_data["HostConfig"].get("NanoCpus", 0)
        assert nanocpus == 1000000000, f"Expected NanoCpus 1000000000, got {nanocpus}"
        print(f"PASS: CPU limit verified ({nanocpus} NanoCpus / 1 CPU)")

        # PID limit check (128)
        pids = inspect_data["HostConfig"]["PidsLimit"]
        assert pids == 128, f"Expected PidsLimit 128, got {pids}"
        print(f"PASS: PID limit verified ({pids})")

        # Security-opt check
        sec_opts = inspect_data["HostConfig"].get("SecurityOpt", [])
        assert any("no-new-privileges" in opt for opt in sec_opts), f"no-new-privileges missing in {sec_opts}"
        print("PASS: Security option 'no-new-privileges' verified")

    finally:
        # Cleanup
        rm_res = subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
        assert rm_res.returncode == 0, f"Cleanup failed: {rm_res.stderr}"
        print(f"PASS: Container cleanup verified ({container_name} removed)")

    print("PASS: test_sample_app_docker_preview_end_to_end")


def main():
    print("Running Sandbox Runner Test Suite...")
    test_missing_arguments_returns_json()
    test_nonexistent_directory_returns_json()
    test_missing_package_json_returns_json()
    test_invalid_port_string_returns_json()
    test_port_out_of_range_returns_json()
    test_sample_app_docker_preview_end_to_end()
    print("ALL TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
