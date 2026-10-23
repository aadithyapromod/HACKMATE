# ==============================================================================
# HackMate - Local Development Launcher
# ==============================================================================

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " Starting HackMate Local Development Services     " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# Check Docker Compose availability
if (Get-Command "docker" -ErrorAction SilentlyContinue) {
    Write-Host "[Info] Docker detected. You can also run 'docker compose up --build'" -ForegroundColor Yellow
}

Write-Host "`nTo run services manually in parallel terminals:" -ForegroundColor White
Write-Host "  Terminal 1 (Backend):" -ForegroundColor Green
Write-Host "    cd backend; python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt; uvicorn app.main:app --reload --port 8000"
Write-Host "  Terminal 2 (Frontend):" -ForegroundColor Green
Write-Host "    cd frontend; npm.cmd install; npm.cmd run dev"
Write-Host "  Terminal 3 (Runner Sandbox - Optional):" -ForegroundColor Green
Write-Host "    cd runner; python -m runner.runner"

Write-Host "`nBackend API: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Frontend UI: http://localhost:3000" -ForegroundColor Cyan
Write-Host "API Docs:    http://localhost:8000/docs`n" -ForegroundColor Cyan
