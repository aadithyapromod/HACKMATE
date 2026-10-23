# HackMate Team Ownership & Responsibilities

With 19 hours to build our hackathon MVP, clear separation of concerns ensures team members work simultaneously without merge conflicts.

---

## Team Roster & Ownership Matrix

| Person | Focus Area | Primary Directories | Working Branch | Key Deliverables |
| :--- | :--- | :--- | :--- | :--- |
| **Person 1** | **Frontend & UX** | `frontend/` | `feature/frontend` | Next.js Dashboard, SSE log streaming listener, code inspection viewer, live app preview iframe, responsive styling. |
| **Person 2** | **Backend & Contracts** | `backend/`, `contracts/` | `feature/backend` | FastAPI REST endpoints, SSE stream broadcaster, project state transitions, repository abstraction, pipeline orchestrator. |
| **Person 3** | **AI Agent Engineering** | `ai/` | `feature/ai` | Prompt engineering for `planner.py` & `generator.py`, schema validation, multi-step React-Vite project synthesis. |
| **Person 4** | **Sandbox & QA** | `runner/`, `docker-compose.yml` | `feature/sandbox` | Isolated Docker build runner, `npm install` and Vite build execution, healthchecks, preview server hosting, test suites. |

---

## Shared / Frozen Zones

The following directories represent system-wide contracts and require mutual agreement before modification:
- `contracts/openapi.yaml`
- `contracts/*.schema.json`
- `docs/API_CONTRACT.md`

Any breaking change to schemas must be communicated to the entire team before merging.
