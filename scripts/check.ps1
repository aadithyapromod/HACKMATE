# ==============================================================================
# HackMate - Verification & Sanity Check Script
# ==============================================================================

$ErrorActionPreference = "Continue"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " HackMate Repository Integrity & Validation Check " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

$allPassed = $true

# 1. Check Required Files
Write-Host "`n[1/5] Checking repository file structure..." -ForegroundColor Yellow
$requiredFiles = @(
    "README.md",
    ".gitignore",
    ".editorconfig",
    ".gitattributes",
    ".env.example",
    "docker-compose.yml",
    "Makefile",
    "docs/ARCHITECTURE.md",
    "docs/API_CONTRACT.md",
    "docs/DATA_MODELS.md",
    "docs/DEVELOPMENT.md",
    "docs/TEAM_OWNERSHIP.md",
    "contracts/openapi.yaml",
    "contracts/project.schema.json",
    "contracts/task.schema.json",
    "contracts/generated-file.schema.json",
    "contracts/agent-event.schema.json",
    "backend/app/main.py",
    "backend/requirements.txt",
    "backend/Dockerfile",
    "ai/planner.py",
    "ai/generator.py",
    "ai/models.py",
    "runner/runner.py",
    "runner/Dockerfile",
    "frontend/package.json",
    "frontend/src/app/page.tsx",
    "frontend/src/lib/api.ts",
    "frontend/src/lib/events.ts",
    "generated/.gitkeep"
)

$missingFiles = 0
foreach ($file in $requiredFiles) {
    if (-not (Test-Path $file)) {
        Write-Host "  MISSING: $file" -ForegroundColor Red
        $missingFiles++
        $allPassed = $false
    }
}

if ($missingFiles -eq 0) {
    Write-Host "  All required scaffold files present." -ForegroundColor Green
} else {
    Write-Host "  $missingFiles required files are missing." -ForegroundColor Red
}

# 2. Check JSON Schemas Validity
Write-Host "`n[2/5] Validating JSON schema files..." -ForegroundColor Yellow
$schemaFiles = Get-ChildItem -Path "contracts/*.schema.json"
foreach ($schema in $schemaFiles) {
    try {
        $content = Get-Content $schema.FullName -Raw | ConvertFrom-Json
        Write-Host "  VALID JSON: $($schema.Name)" -ForegroundColor Green
    } catch {
        Write-Host "  INVALID JSON: $($schema.Name) - $($_.Exception.Message)" -ForegroundColor Red
        $allPassed = $false
    }
}

# 3. Check Python Runtime & Backend Tests
Write-Host "`n[3/5] Checking Python environment & backend tests..." -ForegroundColor Yellow
if (Get-Command "python" -ErrorAction SilentlyContinue) {
    Write-Host "  Python detected. Running pytest in backend if installed..." -ForegroundColor White
    try {
        python -m pytest backend/tests
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Backend tests passed." -ForegroundColor Green
        } else {
            Write-Host "  Backend tests exited with code $LASTEXITCODE." -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  Pytest could not be executed directly. Ensure venv is active." -ForegroundColor Yellow
    }
} else {
    Write-Host "  Python executable not found in PATH. Skipping backend unit test execution." -ForegroundColor Yellow
}

# 4. Check Frontend Dependencies & Type Check
Write-Host "`n[4/5] Checking Frontend configuration..." -ForegroundColor Yellow
if (Test-Path "frontend/node_modules") {
    Write-Host "  node_modules found. Checking frontend build..." -ForegroundColor White
    Push-Location frontend
    npm.cmd run build
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Frontend build passed." -ForegroundColor Green
    } else {
        Write-Host "  Frontend build failed with exit code $LASTEXITCODE." -ForegroundColor Red
        $allPassed = $false
    }
    Pop-Location
} else {
    Write-Host "  frontend/node_modules not yet installed. Run 'npm install' inside frontend." -ForegroundColor Yellow
}

# 5. Git Working Tree Status
Write-Host "`n[5/5] Checking Git Status..." -ForegroundColor Yellow
if (Get-Command "git" -ErrorAction SilentlyContinue) {
    $gitStatus = git status --short
    Write-Host "  Git tracked/untracked state:" -ForegroundColor White
    if ($gitStatus) {
        $gitStatus | ForEach-Object { Write-Host "    $_" -ForegroundColor Cyan }
    } else {
        Write-Host "  Working tree clean." -ForegroundColor Green
    }
}

Write-Host "`n==================================================" -ForegroundColor Cyan
if ($allPassed) {
    Write-Host " Verification completed successfully! " -ForegroundColor Green
} else {
    Write-Host " Verification completed with warnings or missing items. " -ForegroundColor Yellow
}
Write-Host "==================================================" -ForegroundColor Cyan
