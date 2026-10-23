# ==============================================================================
# HackMate - Person 4 Docker Preview Runner & QA Test Suite
# ==============================================================================

$ErrorActionPreference = "Continue"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " HackMate Runner & QA Test Suite Execution        " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# 1. Resolve Python Executable
$pythonCmd = $null
if (Get-Command "python" -ErrorAction SilentlyContinue) {
    try {
        $testPy = & python --version 2>&1
        if ($LASTEXITCODE -eq 0) { $pythonCmd = "python" }
    } catch {}
}

if (-not $pythonCmd -and (Get-Command "py" -ErrorAction SilentlyContinue)) {
    try {
        $testPy = & py --version 2>&1
        if ($LASTEXITCODE -eq 0) { $pythonCmd = "py" }
    } catch {}
}

$mysqlPy = "C:\Program Files\MySQL\MySQL Workbench 8.0 CE\python.exe"
if (-not $pythonCmd -and (Test-Path $mysqlPy)) {
    $env:PYTHONHOME = "C:\Program Files\MySQL\MySQL Workbench 8.0 CE\python"
    $pythonCmd = $mysqlPy
}

if (-not $pythonCmd) {
    Write-Host "[ERROR] No working Python interpreter found!" -ForegroundColor Red
    exit 1
}

Write-Host "Using Python: $pythonCmd" -ForegroundColor Gray

# 2. Run Comprehensive Test Suite
Write-Host "`nRunning Runner Test Suite (Unit, Security, and E2E)..." -ForegroundColor Yellow
& $pythonCmd runner/tests/test_runner.py
$testExit = $LASTEXITCODE

Write-Host "`n==================================================" -ForegroundColor Cyan
if ($testExit -eq 0) {
    Write-Host " All Person 4 Tests Completed Successfully! " -ForegroundColor Green
} else {
    Write-Host " Test Suite Failed with Exit Code: $testExit " -ForegroundColor Red
}
Write-Host "==================================================" -ForegroundColor Cyan
exit $testExit
