# ==============================================================================
# HackMate - Docker Preview Runner End-to-End Validation
# ==============================================================================

$ErrorActionPreference = "Continue"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " HackMate Sandbox Preview Runner Verification     " -ForegroundColor Cyan
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

# 2. Run Test Suite
Write-Host "`n[1/2] Running Runner Tests (validation + E2E)..." -ForegroundColor Yellow
& $pythonCmd sandbox/tests/test_runner.py
$testExit = $LASTEXITCODE

Write-Host "`n==================================================" -ForegroundColor Cyan
if ($testExit -eq 0) {
    Write-Host " Sandbox Verification Completed Successfully! " -ForegroundColor Green
} else {
    Write-Host " Sandbox Verification Failed with Code: $testExit " -ForegroundColor Red
}
Write-Host "==================================================" -ForegroundColor Cyan
exit $testExit
