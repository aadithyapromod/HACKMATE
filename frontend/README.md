# HackMate Frontend Application

Next.js 15 + React 19 + TypeScript + Tailwind CSS developer workspace dashboard for HackMate.

---

## Features

- **Developer Workspace UI:** Dark theme with violet accents.
- **Interactive Project Submission:** Character counter, validation (10–2000 chars), and submission feedback.
- **Real-Time Event Stream:** Server-Sent Events client (`events.ts`) subscribing to `/api/projects/{id}/events`.
- **Typed REST Client:** Fully typed API client (`api.ts`) connecting to `NEXT_PUBLIC_API_URL` (default: `http://localhost:8000`).
- **Dashboard Panes:**
  - Dynamic status bar and timeline.
  - Task execution breakdown list.
  - Live agent activity feed.
  - Source code explorer & viewer.
  - Sandboxed live preview frame.
  - Build & compilation terminal logs.

---

## Local Development

```powershell
cd frontend
npm install
npm run dev
```

The application will be live at: [http://localhost:3000](http://localhost:3000)

Run linter & production build:
```powershell
npm run lint
npm run build
```

---

## Environment Variables

Copy `.env.example` to `.env.local` to override local backend configuration:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```
