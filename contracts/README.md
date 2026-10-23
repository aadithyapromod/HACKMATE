# HackMate API and Schema Contracts

This directory contains the **authoritative API and data model contracts** for the HackMate project.

All frontend, backend, AI orchestration, and runner components MUST adhere strictly to these schemas.

---

## Table of Contents

- [Overview](#overview)
- [Files & Specifications](#files--specifications)
- [Status Lifecycle](#status-lifecycle)
- [Server-Sent Events (SSE) Specification](#server-sent-events-sse-specification)
- [Validation Instructions](#validation-instructions)

---

## Overview

HackMate coordinates 4 modular components:
1. **Frontend:** Next.js dashboard consuming the REST and SSE endpoints.
2. **Backend:** FastAPI service orchestrating project pipelines and event streams.
3. **AI:** Planner and code generator producing React + Vite scaffold and source files.
4. **Runner:** Sandboxed worker executing builds, testing, and preview servers.

---

## Files & Specifications

- [`openapi.yaml`](./openapi.yaml): Full OpenAPI 3.1.0 specification documenting all 8 REST endpoints, parameters, request bodies, response models, and SSE event streaming.
- [`project.schema.json`](./project.schema.json): JSON Schema for Project and ProjectCreate requests.
- [`task.schema.json`](./task.schema.json): JSON Schema for discrete execution tasks.
- [`generated-file.schema.json`](./generated-file.schema.json): JSON Schema for generated source files.
- [`agent-event.schema.json`](./agent-event.schema.json): JSON Schema for real-time SSE stream event envelopes and payloads.

---

## Status Lifecycle

### Project Status Transitions
```
created -> planning -> generating -> building -> testing -> repairing (optional) -> completed
                                                                                 \-> failed
```

Allowed project status values:
- `created`: Project initialized, idea registered.
- `planning`: AI is decomposing the idea into framework tasks.
- `generating`: AI is producing code files.
- `building`: Runner is installing dependencies and building the package.
- `testing`: Runner is verifying smoke tests or dev server readiness.
- `repairing`: (Optional recovery loop) AI fixing build/test errors.
- `completed`: Application successfully generated and ready for preview.
- `failed`: Pipeline terminated due to an unrecoverable error.

### Task Status Values
- `pending`: Waiting to be picked up by an agent.
- `running`: Currently executing.
- `completed`: Successfully executed.
- `failed`: Failed with an error.

---

## Server-Sent Events (SSE) Specification

Endpoint: `GET /api/projects/{id}/events`  
Header: `Accept: text/event-stream`  
Framing:
```text
event: <eventType>
data: <jsonPayload>

```

Allowed `eventType` identifiers:
- `project.status`
- `task.updated`
- `agent.status`
- `build.log`
- `build.completed`
- `preview.ready`
- `project.completed`
- `project.failed`

Client reconnection: The server supports standard browser EventSource reconnects. Upon initial connection, an immediate snapshot event (`project.status`) is emitted.
