# HackMate Execution Sandbox & Frontend Interface Report

## 1. Docker Sandboxing Architecture
- **Controlled Build Image**: Dockerfile configured in `runner-sandbox/Dockerfile` built on `node:20-alpine`.
- **Dropped Privileges**: Runs strictly as an unprivileged non-root user (`uid=1001, gid=1001: sandboxuser`).
- **Resource Limits**:
  - CPU: `--cpus 1.5`
  - Memory: `--memory 1024m`
  - Processes: `--pids-limit 100`
  - Privilege restriction: `--security-opt no-new-privileges:true`
  - Execution watchdog: Strict 120-second timeout.
- **Isolation Guarantee**: The host Docker socket is NEVER mounted into build containers. No host directories outside the assigned `workspace/projects/{id}` are mounted.
- **Cleanup**: Ephemeral build containers are killed and pruned with `--rm` and automatic reaper hooks. Expired project workspaces older than 24 hours are pruned via `workspace_service.cleanup_expired_workspaces()`.

## 2. Professional IDE-Like Code Viewer
- **Collapsible Folder Tree**: `src/components/FolderTree.tsx` generates a dynamic, nested tree matching the exact filesystem hierarchy with custom file-type icons (React/TSX, TypeScript, CSS, JSON, HTML, Markdown).
- **Line Numbers & Editor**: `src/components/CodeViewer.tsx` displays code with line numbers, syntax highlighting powered by PrismJS for TS, JSX, TSX, JS, CSS, JSON, HTML, Python, and Markdown.
- **Safe Relative Paths**: All file lookups are validated against directory traversal and null bytes.
- **Copy & Export**: One-click copy with visual feedback, and one-click ZIP export downloading a clean project archive.

## 3. Sandboxed Live Preview
- **Origin & Header Isolation**: `app/api/preview.py` serves built distribution assets from `dist/` with security headers:
  - `Content-Security-Policy: default-src 'self' 'unsafe-inline' 'unsafe-eval' data: blob: https:; frame-ancestors 'self' http://localhost:3000;`
  - `X-Content-Type-Options: nosniff`
  - `Cache-Control: no-cache`
- **IFrame Sandbox Attributes**: `sandbox="allow-scripts allow-forms allow-same-origin"`.
- **Responsive Viewport Controls**: One-click toggles between Desktop (100%), Tablet (768px), and Mobile (375px).
- **Honest Status**: If a build fails or is in-flight, the preview displays diagnostic logs and error status. It never presents a fake or premature preview.

## 4. Real-time Progress Stepper & Persistence
- **Stages Tracked**: `Analyzing Requirements` $\to$ `Solution Planning` $\to$ `Code Synthesis` $\to$ `Writing Workspace` $\to$ `Sandbox Build & Test` $\to$ `Autonomous Repair` $\to$ `Live Preview Ready`.
- **State Persistence**: On page refresh, the dashboard reads the project ID from URL query parameters or localStorage, fetches project state, tasks, and files from `/api/v2/projects/{id}`, and resumes SSE streaming if the job is active.

## 5. Verification Results
- **Frontend Compilation**: Next.js 15 production build compiled successfully in 6.7s with zero errors (`npm run build`).
- **Backend Test Suite**: 36 automated pytest tests passed in 5.00s (100% pass rate).
