# HACKMATE — Shared Interface Contract

> Every module, endpoint, and data format in this project MUST conform to this contract.

## Module Interfaces

| From | To | Interface |
|---|---|---|
| Backend → AI | AI Service | `create_plan(idea)` and `generate_files(idea, plan)` |
| Backend → Runner | Runner Service | `build_project(project_id, workspace_path)` |
| Frontend → Backend | Backend REST | REST API + SSE event stream |
| AI → Backend | Backend | Plan JSON + files as `{ path, content }` |
| Runner → Backend | Backend | Success/failure, exit code, logs, preview URL |

## Data Formats

### AI → Backend: Plan JSON
```json
{
  "plan": "<step-by-step build plan>",
  "files": [
    { "path": "relative/path/to/file.ext", "content": "<file content>" }
  ]
}
```

### Runner → Backend: Build Result
```json
{
  "success": true,
  "exit_code": 0,
  "logs": "<stdout/stderr>",
  "preview_url": "http://localhost:<port>"
}
```

## REST API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Health check |
| POST | `/api/projects` | Create a new project |
| GET | `/api/projects/{id}` | Get project details |
| POST | `/api/projects/{id}/start` | Start build pipeline |
| GET | `/api/projects/{id}/tasks` | Get task list / progress |
| GET | `/api/projects/{id}/events` | SSE event stream |
| GET | `/api/projects/{id}/files` | Get generated files |
| GET | `/api/projects/{id}/preview` | Get preview URL |

## SSE Event Stream

```
event: status
data: { "stage": "planning"|"generating"|"building"|"done"|"error", "message": "..." }

event: log
data: { "line": "<log line>" }

event: preview
data: { "url": "http://localhost:<port>" }
```

## Function Signatures

### Backend → AI
```python
def create_plan(idea: str) -> dict:       # Returns: { "plan": str }
def generate_files(idea: str, plan: str) -> dict:  # Returns: { "files": [{ "path": str, "content": str }] }
```

### Backend → Runner
```python
def build_project(project_id: str, workspace_path: str) -> dict:
    # Returns: { "success": bool, "exit_code": int, "logs": str, "preview_url": str }
```
