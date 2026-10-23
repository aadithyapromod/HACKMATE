# HackMate Data Models & Status Transitions

This document details the shared models, schema types, and state transition rules implemented across the codebase.

---

## 1. Core Data Models

### 1.1 Project
- `id` (string, required): Format `project-{uuid|nanoid|counter}`.
- `idea` (string, required): Cleaned string, length 10 to 2000 characters.
- `status` (ProjectStatus enum, required): Current pipeline state.
- `created_at` (string ISO-8601 UTC, required): Timestamp when project was created.

### 1.2 Task
- `id` (string, required): Unique task ID (e.g. `task-1`).
- `title` (string, required): Brief title describing the goal.
- `description` (string, required): Detailed prompt or instructions.
- `status` (TaskStatus enum, required): Execution state.

### 1.3 GeneratedFile
- `path` (string, required): Relative file path within generated workspace (e.g., `src/App.jsx`).
- `content` (string, required): Complete text content.

### 1.4 BuildResult
- `success` (boolean, required): Whether compilation / build succeeded.
- `exit_code` (integer, required): Process exit code (0 for success).
- `logs` (string, required): Combined stdout/stderr output.
- `preview_url` (string or null, optional): URL hosting the live preview, or null if inactive.

---

## 2. Status Enums & State Machines

### ProjectStatus
| State | Description | Next Valid States |
| :--- | :--- | :--- |
| `created` | Initial project record created via POST | `planning`, `failed` |
| `planning` | AI agent analyzing requirement & designing architecture | `generating`, `failed` |
| `generating` | AI generating React + Vite files | `building`, `failed` |
| `building` | Runner sandbox running `npm install` & build | `testing`, `repairing`, `failed` |
| `testing` | Runner verifying server launch / smoke tests | `repairing`, `completed`, `failed` |
| `repairing` | Self-healing loop feeding errors back to AI | `building`, `failed` |
| `completed` | Artifacts built and preview server accessible | Terminal state |
| `failed` | Pipeline halted due to unresolvable error | Terminal state |

### TaskStatus
| State | Description |
| :--- | :--- |
| `pending` | Created, waiting to be scheduled |
| `running` | Currently executing |
| `completed` | Finished successfully |
| `failed` | Encountered unhandled error |
