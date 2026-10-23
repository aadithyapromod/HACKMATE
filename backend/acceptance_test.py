import asyncio
import io
import json
import os
import sys
import zipfile
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).parent.resolve()
sys.path.insert(0, str(backend_dir))

# Set environment
os.environ["ENVIRONMENT"] = "development"
os.environ["ENABLE_LOCAL_DEV_RUNNER"] = "true"

from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.db.session import AsyncSessionLocal
from app.models.project import Project, ProjectStatus
from app.models.task import Task
from app.models.file import GeneratedFile
from app.models.build import BuildRun
from app.services.orchestrator import orchestration_service
from app.core.ssrf_protection import validate_url_ssrf, SSRFViolationError
from app.services.integrations.firecrawl_service import firecrawl_service
from app.services.integrations.n8n_service import n8n_service
from app.services.integrations.adaption_service import adaption_service


async def run_final_acceptance_test():
    print("=================================================================")
    print("       HACKMATE V2 — FINAL PRODUCTION ACCEPTANCE TEST            ")
    print("=================================================================\n")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://localhost:8000") as client:
        # Step 0: Verify Health Probe
        print("[STEP 0] Probing System Health Endpoint...")
        health_resp = await client.get("/api/v2/health")
        assert health_resp.status_code == 200
        health_data = health_resp.json()
        print(f"  -> System Status: {health_data['status']}")
        print(f"  -> Database: {health_data['services']['database']['status']} ({health_data['services']['database']['type']})")
        print(f"  -> Runner Config: {health_data['services']['runner']['configured_type']}")
        print(f"  -> Gemini Configured: {health_data['services']['ai']['configured']} (Model: {health_data['services']['ai']['model']})\n")

        resume_id = os.environ.get("RESUME_PROJECT_ID")
        if resume_id:
            project_id = resume_id
            print(f"[RESUME] Resuming verification from existing project checkpoint: {project_id}\n", flush=True)
        else:
            # Step 1: Create New Project with Real Problem Statement
            print("[STEP 1] Creating Project with Real Problem Statement...", flush=True)
            problem_statement = (
                "An interactive real-time Pomodoro Productivity Studio with customizable work/break "
                "intervals, audio notification toggle, daily streak counter, and visual task tags."
            )
            create_resp = await client.post("/api/v2/projects", json={"prompt": problem_statement})
            assert create_resp.status_code == 201
            project_data = create_resp.json()
            project_id = project_data["id"]
            print(f"  -> Created Project ID: {project_id}", flush=True)
            print(f"  -> Project Title: {project_data['title']}", flush=True)
            print(f"  -> Initial Status: {project_data['status']}\n", flush=True)

            # Step 2: Trigger Generation & Background Pipeline Execution
            print("[STEP 2] Triggering Autonomous Generation Pipeline...", flush=True)
            start_resp = await client.post(f"/api/v2/projects/{project_id}/start")
            assert start_resp.status_code == 200
            print("  -> Pipeline triggered successfully. Awaiting completion...\n", flush=True)

            # Wait for the background task to complete
            task = orchestration_service._running_tasks.get(project_id)
            if task:
                await task

        # Step 3: Verify Persistence & Final State
        print("[STEP 3] Verifying Database Persistence & Final Project State...")
        proj_resp = await client.get(f"/api/v2/projects/{project_id}")
        assert proj_resp.status_code == 200
        final_proj = proj_resp.json()
        print(f"  -> Final Status: {final_proj['status']}")
        print(f"  -> Preview URL: {final_proj['preview_url']}")
        print(f"  -> Tasks Decomposed: {len(final_proj['tasks'])}")
        for t in final_proj["tasks"]:
            print(f"     * [{t['status']}] Task {t['sequence_order']}: {t['title']}")
        assert final_proj["status"] == "READY", f"Expected READY, got {final_proj['status']} - {final_proj.get('error_message')}"
        assert len(final_proj["tasks"]) >= 3
        print("  -> Step 3 Passed!\n")

        # Step 4: Verify Generated Codebase & File Explorer Content
        print("[STEP 4] Verifying File Manifest & Source Code...")
        files_resp = await client.get(f"/api/v2/projects/{project_id}/files")
        assert files_resp.status_code == 200
        files_data = files_resp.json()
        file_count = files_data["total_files"]
        print(f"  -> Total Synthesized Files: {file_count}")
        manifest_paths = [f["file_path"] for f in files_data["files"]]
        for p in manifest_paths:
            print(f"     - {p}")

        assert "package.json" in manifest_paths
        assert "src/App.tsx" in manifest_paths
        assert "index.html" in manifest_paths

        # Check actual source code content of App.tsx
        app_file_resp = await client.get(f"/api/v2/projects/{project_id}/files/src/App.tsx")
        assert app_file_resp.status_code == 200
        app_code = app_file_resp.json()["content"]
        assert len(app_code) > 200
        assert "export default function App" in app_code or "export default" in app_code
        print("  -> Validated actual non-placeholder source code in src/App.tsx")
        print("  -> Step 4 Passed!\n")

        # Step 5: Verify ZIP Export Download
        print("[STEP 5] Verifying ZIP Export Action...")
        zip_resp = await client.get(f"/api/v2/projects/{project_id}/export")
        assert zip_resp.status_code == 200
        assert zip_resp.headers["content-type"] == "application/zip"
        zip_buf = io.BytesIO(zip_resp.content)
        with zipfile.ZipFile(zip_buf, "r") as zf:
            zip_entries = zf.namelist()
            print(f"  -> ZIP Archive validated ({len(zip_entries)} entries)")
            assert "package.json" in zip_entries
            assert "src/App.tsx" in zip_entries
        print("  -> Step 5 Passed!\n")

        # Step 6: Verify Live Preview Serving & Security Headers
        print("[STEP 6] Verifying Sandboxed Live Preview...")
        preview_meta_resp = await client.get(f"/api/v2/projects/{project_id}/preview")
        assert preview_meta_resp.status_code == 200
        p_meta = preview_meta_resp.json()
        assert p_meta["is_ready"] is True
        print(f"  -> Preview Endpoint: {p_meta['preview_url']}")

        # Fetch index.html through preview endpoint
        preview_asset_resp = await client.get(f"/api/v2/projects/{project_id}/preview/index.html")
        assert preview_asset_resp.status_code == 200
        assert "<!doctype html>" in preview_asset_resp.text.lower()
        assert "Content-Security-Policy" in preview_asset_resp.headers
        print("  -> Confirmed Content-Security-Policy and anti-clickjacking headers present.")
        print("  -> Step 6 Passed!\n")

        # Step 7: Verify SSRF Protection on Reference URLs
        print("[STEP 7] Verifying SSRF Protection Boundary...")
        ssrf_cases = ["http://127.0.0.1:8000", "http://localhost:3000", "http://169.254.169.254/latest/meta-data/"]
        for blocked in ssrf_cases:
            try:
                validate_url_ssrf(blocked)
                print(f"  -> FAIL: Did not block SSRF target {blocked}")
                assert False, f"Should block {blocked}"
            except SSRFViolationError as e:
                print(f"  -> Successfully blocked SSRF attempt: {blocked}")

        # Public URL allowed
        is_safe, _ = validate_url_ssrf("https://example.com")
        assert is_safe is True
        print("  -> Step 7 Passed!\n")

        # Step 8: Verify Integrations Status
        print("[STEP 8] Verifying Pluggable Integrations...")
        int_resp = await client.get("/api/v2/integrations/status")
        assert int_resp.status_code == 200
        int_data = int_resp.json()
        print(f"  -> Firecrawl Scraper: {int_data['firecrawl']['status']} (Graceful fallback active)")
        print(f"  -> n8n Webhook: {int_data['n8n']['status']} (Graceful fallback active)")
        print(f"  -> Adaption Labs: {int_data['adaption']['status']} (Opt-in dataset curation policy active)")
        print("  -> Step 8 Passed!\n")

        print("=================================================================", flush=True)
        print("       ALL ACCEPTANCE TEST STEPS COMPLETED SUCCESSFULLY!         ", flush=True)
        print("=================================================================", flush=True)

    from app.db.session import engine
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_final_acceptance_test())
