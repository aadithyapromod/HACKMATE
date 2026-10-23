# HackMate API Contract

This document provides the authoritative REST and Server-Sent Events (SSE) contract for all communication between the HackMate Frontend, Backend, and External Clients.

---

## Base URLs

- **Local Development:** `http://localhost:8000`
- **Docker Compose:** `http://backend:8000`

---

## 1. Endpoints

### 1.1 `GET /api/health`
Checks server readiness.

- **Response `200 OK`:**
```json
{
  "status": "ok",
  "service": "hackmate-backend",
  "timestamp": "2026-10-23T10:00:00Z"
}
```

---

### 1.2 `POST /api/projects`
Creates a new project from a hackathon concept.

- **Request Body:**
```json
{
  "idea": "Build a student hackathon matching website"
}
```
*Validation:* `idea` must be between 10 and 2000 characters after trimming whitespace.

- **Response `201 Created`:**
```json
{
  "id": "project-123",
  "idea": "Build a student hackathon matching website",
  "status": "created",
  "created_at": "2026-10-23T10:00:00Z"
}
```

- **Response `400 Bad Request`:**
```json
{
  "detail": "Idea must be between 10 and 2000 characters after trimming whitespace."
}
```

---

### 1.3 `GET /api/projects/{id}`
Retrieves current project status and metadata.

- **Response `200 OK`:**
```json
{
  "id": "project-123",
  "idea": "Build a student hackathon matching website",
  "status": "planning",
  "created_at": "2026-10-23T10:00:00Z"
}
```

- **Response `404 Not Found`:**
```json
{
  "detail": "Project not found"
}
```

---

### 1.4 `POST /api/projects/{id}/start`
Triggers the agentic pipeline for the project. Returns truthful current execution status.

- **Response `200 OK`:**
```json
{
  "id": "project-123",
  "idea": "Build a student hackathon matching website",
  "status": "planning",
  "created_at": "2026-10-23T10:00:00Z"
}
```

---

### 1.5 `GET /api/projects/{id}/tasks`
Retrieves all pipeline subtasks. Returns an empty array `[]` if no tasks exist yet.

- **Response `200 OK`:**
```json
[
  {
    "id": "task-1",
    "title": "Decompose requirements",
    "description": "Analyze hackathon idea and determine React component layout",
    "status": "completed"
  },
  {
    "id": "task-2",
    "title": "Generate application files",
    "description": "Generate the React application source",
    "status": "running"
  }
]
```

---

### 1.6 `GET /api/projects/{id}/events`
Establishes a Server-Sent Events stream.

- **Response Headers:**
  - `Content-Type: text/event-stream`
  - `Cache-Control: no-cache`
  - `Connection: keep-alive`

- **Wire Format:**
```text
event: <event_type>
data: <json_string>

```

---

### 1.7 `GET /api/projects/{id}/files`
Retrieves generated source code files. Returns empty files list `{"files": []}` if generation hasn't started.

- **Response `200 OK`:**
```json
{
  "files": [
    {
      "path": "src/App.jsx",
      "content": "export default function App() { return <h1>Hello</h1>; }"
    }
  ]
}
```

---

### 1.8 `GET /api/projects/{id}/preview`
Retrieves build logs and preview server status.

- **Response `200 OK`:**
```json
{
  "success": true,
  "exit_code": 0,
  "logs": "Build succeeded",
  "preview_url": null
}
```

---

## 2. Server-Sent Events Detail

| Event Type | Description | Sample Data Payload |
| :--- | :--- | :--- |
| `project.status` | Emitted when overall status transitions | `{"project_id":"project-123","status":"generating"}` |
| `task.updated` | Emitted when a subtask is created or changes state | `{"task_id":"task-1","title":"Scaffold Vite","status":"completed"}` |
| `agent.status` | Emitted by AI agents during active thought or synthesis | `{"agent":"Coder","status":"running","message":"Writing src/App.jsx"}` |
| `build.log` | Emitted during sandbox compilation / npm execution | `{"chunk":"vite v5.0.0 building for production...\n"}` |
| `build.completed`| Emitted when build finishes | `{"success":true,"exit_code":0}` |
| `preview.ready` | Emitted when Vite preview/dev server is accessible | `{"preview_url":"http://localhost:4173"}` |
| `project.completed` | Emitted when all tasks and builds finish successfully | `{"project_id":"project-123","duration_seconds":42}` |
| `project.failed` | Emitted when pipeline aborts | `{"project_id":"project-123","error":"Compilation failed"}` |
