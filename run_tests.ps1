# ==============================================================================
# OrderFlow Sentinel - Full Regression Test Suite Execution
# ==============================================================================
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$WorkspaceRoot = $PSScriptRoot
Set-Location $WorkspaceRoot

Write-Host "`n=== OrderFlow Sentinel: Full Regression Test Suite ===" -ForegroundColor Cyan

$PythonExe = Join-Path $WorkspaceRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Host "[ERROR] Virtual environment not found at $PythonExe" -ForegroundColor Red
    exit 1
}

# 1. Record database order count before tests
$DbPath = Join-Path $WorkspaceRoot "orderflow_sentinel.db"
$OrdersBefore = $null
if (Test-Path $DbPath) {
    $OrdersBefore = & $PythonExe -c "import sqlite3; conn = sqlite3.connect('orderflow_sentinel.db'); print(conn.cursor().execute('SELECT COUNT(*) FROM orders').fetchone()[0])"
    Write-Host "[INFO] Persistent development DB active orders before tests: $OrdersBefore" -ForegroundColor Cyan
}

# 2. Run Backend Pytest Suite with Database Isolation
Write-Host "`n[1/2] Running Backend Pytest Suite (46 Tests with DB Isolation)..." -ForegroundColor Cyan
& $PythonExe -m pytest backend/tests -v
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Backend tests failed with exit code $LASTEXITCODE!" -ForegroundColor Red
    exit $LASTEXITCODE
}
Write-Host "[PASS] Backend test suite passed cleanly!" -ForegroundColor Green

# 3. Verify Database Isolation Safeguard
if ($OrdersBefore -ne $null) {
    $OrdersAfter = & $PythonExe -c "import sqlite3; conn = sqlite3.connect('orderflow_sentinel.db'); print(conn.cursor().execute('SELECT COUNT(*) FROM orders').fetchone()[0])"
    Write-Host "[INFO] Persistent development DB active orders after tests: $OrdersAfter" -ForegroundColor Cyan
    if ($OrdersBefore -eq $OrdersAfter) {
        Write-Host "[PASS] Database Isolation Verified: 0 synthetic test records added to persistent database." -ForegroundColor Green
    } else {
        Write-Host "[WARN] Persistent database order count changed ($OrdersBefore -> $OrdersAfter). Isolation check failed!" -ForegroundColor Yellow
    }
}

# 4. Run Frontend Unit Test Suite
Write-Host "`n[2/2] Running Frontend Unit Test Suite..." -ForegroundColor Cyan
$NodePath = "C:\Users\Asus\AppData\Local\Microsoft\WinGet\Packages\OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe\node-v24.20.0-win-x64"
if (Test-Path $NodePath) {
    $env:Path = "$NodePath;" + $env:Path
}

Set-Location (Join-Path $WorkspaceRoot "frontend")
& npm.cmd test
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Frontend tests failed with exit code $LASTEXITCODE!" -ForegroundColor Red
    Set-Location $WorkspaceRoot
    exit $LASTEXITCODE
}
Set-Location $WorkspaceRoot

Write-Host "`n====================================================="
Write-Host "[SUCCESS] All Backend and Frontend Tests Passed Cleanly!" -ForegroundColor Green
Write-Host "=====================================================`n"

