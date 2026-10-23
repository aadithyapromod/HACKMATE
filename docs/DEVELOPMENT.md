# HackMate Development Guide

This guide outlines setup instructions, daily development workflows, testing commands, and git etiquette for the HackMate team on Windows and cross-platform environments.

---

## 1. Prerequisites

- **Node.js**: v20+ LTS or v24+ (Node v24.22.1 and npm 11.19.1 tested)
- **Python**: 3.11 or higher
- **PowerShell**: 7.x or Windows PowerShell 5.1
- **Docker & Docker Compose** (optional for local mock mode, required for full sandbox)
- **Git**

> **PowerShell Execution Policy Note:** If Windows blocks scripts (`.ps1`), run scripts with `-ExecutionPolicy Bypass` or execute commands directly using `npm.cmd` / Python virtual environments.

---

## 2. Quick Local Setup

### 2.1 Backend Setup
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
Backend API will be accessible at: `http://localhost:8000`  
Interactive Swagger docs: `http://localhost:8000/docs`

### 2.2 Frontend Setup
```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```
Frontend Dashboard will be accessible at: `http://localhost:3000`

### 2.3 Runner Setup
```powershell
cd runner
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m runner.runner
```

---

## 3. Running with Docker Compose

To start all services together:
```powershell
docker compose up --build
```

---

## 4. Verification and Testing

Run the automated check script:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1
```

Or run individual component tests:

- **Backend tests:**
  ```powershell
  cd backend
  pytest
  ```

- **Frontend lint and build:**
  ```powershell
  cd frontend
  npm.cmd run lint
  npm.cmd run build
  ```

---

## 5. Git Workflow & Team Branches

We follow a feature branch workflow off `main`:

```text
main
├── feature/frontend    (Person 1: UI & SSE Client)
├── feature/backend     (Person 2: FastAPI, Storage, & Orchestration)
├── feature/ai          (Person 3: Planner & Generator Agents)
└── feature/sandbox     (Person 4: Docker Runner & Preview Server)
```

### Daily Git Steps:
1. Fetch latest changes: `git fetch origin`
2. Keep feature branch updated: `git rebase origin/main`
3. Never force-push to `main`.
4. Open PRs targeting `main` and run `check.ps1` before merging.
