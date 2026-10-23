# HackMate Runner Sandbox

Isolated execution environment for building, validating, and previewing generated React + Vite applications.

---

## Security Architecture

1. **Host Protection:** Generated applications are **never** built or executed on the host system. All builds happen strictly inside a dedicated Docker container running as a non-privileged user (`runneruser`, UID 1001).
2. **Resource Constraints:** The runner container runs with restricted CPU, memory (1GB limit), and PID limits (`pids_limit: 100`).
3. **No Docker Socket Mounting:** The Docker daemon socket is intentionally NOT mounted into the container to prevent container breakout vulnerabilities.

---

## Runner Interface

- `build_project(project_id: str, workspace_path: str) -> dict`
  - Runs in-container `npm install` and `npm run build`.
  - Returns:
    ```json
    {
      "success": true,
      "exit_code": 0,
      "logs": "npm install completed...\nvite build finished in 1.2s",
      "preview_url": "http://localhost:4173"
    }
    ```

---

## Local Development & Testing

```powershell
cd runner
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest
```
