# HackMate Architecture

This document describes the high-level system architecture, request flow, component interactions, and execution lifecycle of **HackMate**.

---

## 1. System Overview

HackMate is an agentic AI hackathon companion designed to take a high-level project idea and autonomously produce, build, test, and preview a working React + Vite application within minutes.

```mermaid
flowchart TD
    User([User / Browser]) <-->|Next.js UI / SSE| Frontend[frontend/ Next.js App]
    Frontend <-->|REST & SSE Stream| Backend[backend/ FastAPI]
    Backend <-->|In-Memory / SQLite Repository| Storage[(Storage Layer)]
    Backend -->|Plan & Generate Code| AI[ai/ Planner & Generator]
    Backend -->|Run Builds & Tests| Runner[runner/ Sandboxed Runner]
    Runner -->|Static Output / Preview Port| PreviewServer[React + Vite Preview Server]
    PreviewServer -.->|Live App IFrame| Frontend
```

---

## 2. Component Roles

| Component | Technology | Primary Responsibility |
| :--- | :--- | :--- |
| **Frontend** (`frontend/`) | Next.js 15, React 19, TypeScript, Tailwind CSS | Dashboard UI, idea submission, real-time agent/build log feeds, code inspection, interactive preview. |
| **Backend** (`backend/`) | Python 3.11+, FastAPI, Pydantic, Uvicorn | Project management, SSE event multiplexing, orchestrator triggering, API contract enforcement. |
| **AI Agents** (`ai/`) | Python, LangChain / Direct SDKs (OpenAI/Gemini/Anthropic) | Prompt decomposition into tasks (`planner.py`) and code synthesis (`generator.py`). |
| **Runner** (`runner/`) | Docker, Python, Node.js / Vite | Isolated environment executing `npm install`, `npm run build`, and preview hosting. |
| **Contracts** (`contracts/`) | OpenAPI 3.1, JSON Schemas | Single source of truth for all schemas and endpoint contracts. |

---

## 3. End-to-End Execution Flow

```mermaid
sequenceDiagram
    autonumber
    actor U as Developer
    participant FE as Frontend (Next.js)
    participant BE as Backend (FastAPI)
    participant AI as AI Agents
    participant RN as Runner Sandbox

    U->>FE: Submits idea & clicks "Start Building"
    FE->>BE: POST /api/projects (idea: 10-2000 chars)
    BE-->>FE: 201 Created (Project: id, status='created')
    FE->>BE: GET /api/projects/{id}/events (SSE connection)
    FE->>BE: POST /api/projects/{id}/start
    BE-->>FE: 200 OK (status='planning')

    Note over BE,AI: Orchestration Step 1: Planning
    BE->>BE: Broadcast SSE 'project.status' -> 'planning'
    BE->>AI: create_plan(idea)
    AI-->>BE: PlanData (Framework: react-vite, Tasks: [T1, T2, ...])
    BE->>BE: Broadcast SSE 'task.updated' for each task

    Note over BE,AI: Orchestration Step 2: Generation
    BE->>BE: Broadcast SSE 'project.status' -> 'generating'
    BE->>AI: generate_files(idea, plan)
    AI-->>BE: FileListResponse (src/App.jsx, package.json, etc.)
    BE->>BE: Persist files to workspace

    Note over BE,RN: Orchestration Step 3: Build & Test
    BE->>BE: Broadcast SSE 'project.status' -> 'building'
    BE->>RN: build_project(project_id, workspace_path)
    RN->>BE: Stream logs via SSE ('build.log')
    RN-->>BE: BuildResult (success=true, preview_url="http://localhost:4173")
    BE->>BE: Broadcast SSE 'build.completed' & 'preview.ready'
    BE->>BE: Broadcast SSE 'project.status' -> 'completed'
    FE->>U: Displays preview in IFrame & enables code viewer
```

---

## 4. Security & Sandbox Boundary

1. **Isolation Guarantee:** Generated code is never executed directly on the host operating system. Build and execution runs within an isolated Docker container with dropped privileges (`no-new-privileges:true`), CPU/memory limits, and restricted networking.
2. **Read-Only Code Integrity:** Workspace files are validated prior to execution to prevent path traversal (`../`) attacks outside the project's generated sandbox folder.
3. **Graceful Fallbacks:** In development environments without active LLM keys or Docker daemon access, both the AI agent module and the Runner module provide deterministic mock responses for end-to-end testing.
