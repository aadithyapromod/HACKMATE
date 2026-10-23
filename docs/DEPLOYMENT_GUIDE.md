# HackMate v2 Production Deployment & Operations Manual

This guide outlines the production deployment of HackMate on **Render** with a custom `.xyz` domain, managed PostgreSQL database, and zero secret leakage.

---

## 1. Architecture Topology on Render

```mermaid
flowchart TD
    Client(["User Browser"]) <-->|HTTPS / Custom Domain (.xyz)| FE["Frontend: Next.js 15 Web Service"]
    FE <-->|REST & SSE (/api/v2)| BE["Backend: FastAPI Web Service"]
    BE <-->|Async Engine (asyncpg)| PG[("Managed PostgreSQL Database")]
    BE -->|API Key (Server Secret)| Gemini["Google Gemini API"]
    BE -.->|Optional API Key| Firecrawl["Firecrawl Scraper API"]
    BE -.->|Optional HMAC Webhook| N8N["n8n Instance"]
```

---

## 2. Step-by-Step Deployment via Render Blueprint

### Step 1: Connect Git Repository to Render
1. Push `hackmate-core/` to your private GitHub repository.
2. In the [Render Dashboard](https://dashboard.render.com), click **New +** $\to$ **Blueprint**.
3. Select your repository. Render will automatically parse [`hackmate-core/render.yaml`](file:///c:/Users/aadit/OneDrive/Documents/hackmate-core/render.yaml).

### Step 2: Configure Production Secrets
Render will prompt for the non-synced environment variables declared in `render.yaml`.
Configure the following secrets in the Render Dashboard (never commit these to source code):

| Secret Name | Service | Description | Required? |
|---|---|---|---|
| `GEMINI_API_KEY` | `hackmate-backend` | Your Google Gemini API Key | **Yes (Mandatory)** |
| `FIRECRAWL_API_KEY` | `hackmate-backend` | Firecrawl Scraper Key | *Optional* |
| `N8N_WEBHOOK_URL` | `hackmate-backend` | Target n8n Webhook URL | *Optional* |
| `N8N_WEBHOOK_SECRET`| `hackmate-backend` | HMAC SHA-256 Webhook Signing Secret | *Optional* |
| `ADAPTION_API_KEY` | `hackmate-backend` | Adaption Labs API Key | *Optional* |

### Step 3: Deployment Execution
1. Click **Apply**.
2. Render provisions:
   - `hackmate-postgres`: Managed PostgreSQL instance.
   - `hackmate-backend`: Python 3.11+ web service with Alembic auto-migration and uvicorn.
   - `hackmate-frontend`: Node 20+ web service with Next.js 15 production build.
3. Once deployed, verify backend health at:
   `https://<your-backend-service>.onrender.com/api/v2/health`

---

## 3. Custom Domain Configuration (`.xyz`)

To map your registered `.xyz` custom domain (e.g. `hackmate.xyz` or `app.hackmate.xyz`):

### A. Add Domain in Render
1. In the Render Dashboard, navigate to your **`hackmate-frontend`** service.
2. Under **Settings** $\to$ **Custom Domains**, click **Add Custom Domain**.
3. Enter your domain: `app.yourdomain.xyz` (or `yourdomain.xyz`).

### B. Configure DNS Records with Your Domain Registrar
Log in to your domain registrar (Namecheap, Porkbun, Cloudflare, GoDaddy, etc.) and add the exact DNS records provided by Render:

#### For Subdomains (e.g. `app.yourdomain.xyz`):
| Type | Name / Host | Value / Target | TTL |
|---|---|---|---|
| **CNAME** | `app` | `hackmate-frontend.onrender.com` | Automatic / 300s |

#### For Apex / Root Domains (e.g. `yourdomain.xyz`):
| Type | Name / Host | Value / Target | TTL |
|---|---|---|---|
| **ALIAS / ANAME** | `@` | `hackmate-frontend.onrender.com` | Automatic |
| *(or A Record)* | `@` | `216.24.57.1` (Verify exact IP in Render UI) | 300s |

### C. SSL / TLS Certificate Verification
- Render automatically provisions a Let's Encrypt SSL certificate once DNS propagates.
- Update `CORS_ORIGINS` in your `hackmate-backend` service environment variables:
  ```bash
  CORS_ORIGINS=https://app.yourdomain.xyz,https://yourdomain.xyz
  ```

---

## 4. Execution Sandbox Security on Render

- Standard cloud web services run inside unprivileged container instances and do not permit mounting the host `/var/run/docker.sock`.
- HackMate natively handles this on Render by running the execution sandbox with:
  - Non-root user execution (`uid=1001`).
  - Strict subprocess isolation with memory limits and `asyncio.wait_for` watchdog (120s timeout).
  - Canonical workspace containment (`Path.is_relative_to()`), strictly preventing directory breakouts.
  - Zero exposure of the host filesystem or internal Docker daemon.

---

## 5. Health Monitoring, Logging & Rollback Plan

### Monitoring & Readiness Probes
- **Readiness URL**: `GET /api/v2/health`
  - Validates PostgreSQL connectivity, Gemini configuration, and runner status.
  - Render automatically monitors this endpoint every 10 seconds to route traffic only to healthy instances.

### Production Logging
- Real-time application logs stream to the Render Log Viewer.
- Standard structured logging outputs timestamp, level, and module:
  `2026-10-24 02:00:00 [INFO] hackmate.core: Database schema initialized successfully.`

### Rollback Plan
If an unexpected regression occurs in production:
1. In the Render Dashboard, navigate to **Deploys**.
2. Select the previous stable deployment commit.
3. Click **Rollback to this deploy**.
4. Render immediately pivots traffic to the previous verified build.
