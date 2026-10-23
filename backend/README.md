# HackMate Backend Service

FastAPI-powered orchestrator and REST/SSE API for HackMate.

---

## Responsibilities

- Exposes the authoritative HackMate REST & SSE endpoints.
- Validates requests using Pydantic models conforming to `/contracts/`.
- Manages project state transitions (`created` -> `planning` -> `generating` -> ...).
- Emits real-time progress updates via Server-Sent Events (`/api/projects/{id}/events`).
- Bridges the AI agent generator with the isolated runner environment.

---

## Local Setup & Run

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Verify health:
```powershell
curl http://localhost:8000/api/health
```

Run test suite:
```powershell
pytest
```

---

## Implemented vs. Remaining Work

- [x] In-memory repository abstraction (`storage/repository.py`).
- [x] All 8 API endpoints with contract-compliant schemas.
- [x] SSE event broadcasting channel per project.
- [x] Validation of hackathon idea length (10-2000 characters).
- [ ] SQLite/PostgreSQL persistence backing repository interface.
- [ ] Background pipeline async worker queue integration with AI client and runner client.
