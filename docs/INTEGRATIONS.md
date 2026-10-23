# HackMate Integrations Specification & Security Manual

This document outlines the architecture, security constraints, and configuration contracts for HackMate's three optional pluggable integrations: **Firecrawl**, **n8n**, and **Adaption Labs**.

---

## 1. Firecrawl (Reference Website Scraper)

### Purpose
When a user provides an optional reference website URL (e.g. `https://dribbble.com/shots/...` or a competitor landing page), Firecrawl extracts structure, navigation hierarchy, and layout cues to guide Gemini's solution planning.

### Security Architecture & SSRF Defense
Server-Side Request Forgery (SSRF) protection is enforced by `app/core/ssrf_protection.py` before any network call:
- **Protocol Whitelist**: Only `http://` and `https://` are permitted. Schemes like `file://`, `ftp://`, `gopher://` are rejected.
- **DNS & IP Range Filtering**: DNS hostnames are resolved before connection. The following IP ranges are blocked:
  - `127.0.0.0/8`, `::1` (Loopback)
  - `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` (Private RFC 1918)
  - `169.254.0.0/16`, `fe80::/10` (Link-local & AWS/GCP/Azure Cloud Metadata `169.254.169.254`)
  - `0.0.0.0/8`, `224.0.0.0/4`, `240.0.0.0/4` (Reserved/Broadcast)
  - Reserved hostnames: `localhost`, `*.internal`, `*.local`.
- **Untrusted Data Boundary**: Scraped markdown is stripped of HTML scripts and CSS style tags, truncated to at most 1,800 characters, and passed to Gemini inside an explicit untrusted reference delimiter. Gemini is instructed never to treat the scraped text as executable instructions or copy proprietary source code.

### Configuration
- Environment variable in `backend/.env`:
  ```bash
  FIRECRAWL_API_KEY=fc-YOUR_API_KEY_HERE
  ```
- Graceful Degradation: If `FIRECRAWL_API_KEY` is omitted or empty, reference scraping is silently bypassed and the core pipeline continues using the user's natural language prompt.

---

## 2. n8n (Workflow Automation & Post-Generation Notifications)

### Purpose
Allows automated external post-processing pipelines (e.g. notifying a team Slack channel, generating an executive summary, or uploading builds to GitHub) when a project lifecycle completes.

### Security Architecture & Webhook Contract
- **Server-Side Enforcement**: The webhook URL is strictly read from `N8N_WEBHOOK_URL` in `backend/.env`. End users cannot submit arbitrary webhook endpoints.
- **HMAC SHA-256 Signatures**: Each request carries an `X-HackMate-Signature: sha256=<hash>` generated with `N8N_WEBHOOK_SECRET` so the n8n instance can verify request authenticity.
- **Idempotency Token**: Each request includes a unique UUID in `X-HackMate-Delivery-Id`.
- **Minimal Data Surface**: Payloads contain only non-sensitive metadata (`project_id`, `title`, `status`, `preview_url`, `timestamp`). No source code, passwords, or LLM keys are ever transmitted.
- **Non-blocking Dispatch**: Dispatches asynchronously with a 5.0s timeout. Failure of n8n never disrupts the website generation pipeline.

### Documented n8n Workflow Blueprint
```text
[Webhook Trigger Node] 
      │ (POST /webhook/hackmate-events)
      ▼
[Crypto / Header Validation Node] ──► Verify X-HackMate-Signature matches HMAC(body, secret)
      │
      ▼
[Switch / Router Node]
      ├─► Case 'project.ready' ─────► [Slack Node / Discord Node] (Send live preview URL & celebration)
      ├─► Case 'project.failed' ────► [Alert Node] (Send error summary to developer)
      └─► Case 'test.ping' ─────────► [HTTP 200 Response Node]
```

### Configuration
```bash
N8N_WEBHOOK_URL=https://your-n8n-instance.com/webhook/hackmate-events
N8N_WEBHOOK_SECRET=your_optional_webhook_signing_secret
```

---

## 3. Adaption Labs (Model Experimentation & Dataset Preparation)

### Capability Analysis
- **Platform**: Adaption Labs (`adaptionlabs.ai`) is an automated model training, data generation (`Invent`), and recipe co-optimization platform (`AutoScientist`).
- **Concrete Use Case for HackMate**: Curating, profiling, and evaluating golden prompt-completion datasets for training specialized offline React+Vite web app generators. It is **NOT** a runtime code generation inference API and does not replace Gemini.

### Safety & Governance Guardrails
1. **Explicit User Opt-In**: `app/services/integrations/adaption_service.py` strictly raises `AdaptionConsentError` if `user_opt_in=True` is not provided. Private user projects are never uploaded or shared without explicit user authorization.
2. **Cost & Quota Awareness**: Dataset uploads and AutoScientist hyperparameter optimization runs consume compute units on Adaption Labs.
3. **Disabled by Default**: `ADAPTION_API_KEY` remains empty and disabled by default until the operator chooses to train specialized models.

### Configuration
```bash
ADAPTION_API_KEY=
```

---

## 4. Verification Endpoints

The FastAPI gateway exposes endpoints to monitor and test integrations:
- `GET /api/v2/integrations/status`: Returns operational status of all three integrations.
- `POST /api/v2/integrations/firecrawl/test`: Tests a real scrape against a safe URL (`https://example.com`).
- `POST /api/v2/integrations/n8n/test`: Dispatches a signed test ping event to verify the webhook receiver.
- `GET /api/v2/integrations/adaption/info`: Returns capabilities, data retention, and consent policy.
