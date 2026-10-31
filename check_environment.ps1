# ==============================================================================
# OrderFlow Sentinel - Environment & Prerequisite Health Check
# ==============================================================================
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Write-Host "`n=== OrderFlow Sentinel: Environment Verification ===" -ForegroundColor Cyan

$WorkspaceRoot = $PSScriptRoot
Set-Location $WorkspaceRoot

$AllPassed = $true

# 1. Check Python Virtual Environment
Write-Host "`n[1/5] Checking Python Virtual Environment..." -NoNewline
$PythonExe = Join-Path $WorkspaceRoot ".venv\Scripts\python.exe"
if (Test-Path $PythonExe) {
    try {
        $PyVersion = & $PythonExe --version
        Write-Host " [PASS] ($PyVersion)" -ForegroundColor Green
    } catch {
        Write-Host " [WARN] Python executable found at .venv but failed to execute: $_" -ForegroundColor Yellow
        $AllPassed = $false
    }
} else {
    Write-Host " [FAIL] Python venv not found at .venv\Scripts\python.exe" -ForegroundColor Red
    $AllPassed = $false
}

# 2. Check Node.js and npm
Write-Host "[2/5] Checking Node.js and npm..." -NoNewline
$NodePath = "C:\Users\Asus\AppData\Local\Microsoft\WinGet\Packages\OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe\node-v24.20.0-win-x64"
if (Test-Path $NodePath) {
    $env:Path = "$NodePath;" + $env:Path
}

try {
    $NodeVer = (node -v 2>$null)
    $NpmVer = (npm.cmd -v 2>$null)
    if ($NodeVer -and $NpmVer) {
        Write-Host " [PASS] (Node: $NodeVer, npm: $NpmVer)" -ForegroundColor Green
    } else {
        Write-Host " [FAIL] Node or npm not found in PATH." -ForegroundColor Red
        $AllPassed = $false
    }
} catch {
    Write-Host " [FAIL] Error probing Node/npm: $_" -ForegroundColor Red
    $AllPassed = $false
}

# 3. Check SQLite Persistent Database
Write-Host "[3/5] Checking Persistent SQLite Database..." -NoNewline
$DbPath = Join-Path $WorkspaceRoot "orderflow_sentinel.db"
if (Test-Path $DbPath) {
    try {
        $OrderCount = & $PythonExe -c "import sqlite3; conn = sqlite3.connect('orderflow_sentinel.db'); print(conn.cursor().execute('SELECT COUNT(*) FROM orders').fetchone()[0])"
        Write-Host " [PASS] (Found: $DbPath with $OrderCount active orders)" -ForegroundColor Green
    } catch {
        Write-Host " [WARN] Database exists but query failed: $_" -ForegroundColor Yellow
    }
} else {
    Write-Host " [INFO] orderflow_sentinel.db not yet created (will initialize on first startup)" -ForegroundColor Yellow
}

# 4. Check Environment Configuration (.env)
Write-Host "[4/5] Checking Configuration (.env)..." -NoNewline
$EnvPath = Join-Path $WorkspaceRoot ".env"
if (Test-Path $EnvPath) {
    Write-Host " [PASS] (.env file exists)" -ForegroundColor Green
} else {
    Write-Host " [WARN] .env missing. Copying from .env.example..." -ForegroundColor Yellow
    Copy-Item (Join-Path $WorkspaceRoot ".env.example") $EnvPath
    Write-Host "        Created .env from .env.example" -ForegroundColor Green
}

# 5. Check Compiled Production Frontend
Write-Host "[5/5] Checking Compiled Frontend Distribution..." -NoNewline
$DistIndex = Join-Path $WorkspaceRoot "frontend\dist\index.html"
if (Test-Path $DistIndex) {
    Write-Host " [PASS] (Compiled SPA bundle present in frontend\dist)" -ForegroundColor Green
} else {
    Write-Host " [INFO] frontend\dist missing. Run .\build_frontend.ps1 to generate production SPA bundle." -ForegroundColor Yellow
}

Write-Host "`n-----------------------------------------------------"
if ($AllPassed) {
    Write-Host "Environment is ready! You can run the platform using:" -ForegroundColor Green
    Write-Host "  - .\run_backend.ps1   (Production-style on http://localhost:8000/ui)" -ForegroundColor White
    Write-Host "  - .\run_frontend.ps1  (Vite dev server on http://localhost:3000)" -ForegroundColor White
    Write-Host "  - .\run_tests.ps1     (Full regression test suite)" -ForegroundColor White
} else {
    Write-Host "Environment check detected missing items. Please see errors above." -ForegroundColor Red
}
Write-Host "=====================================================`n"

