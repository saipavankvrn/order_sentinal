# ==============================================================================
# OrderFlow Sentinel - Launch FastAPI Backend Server
# ==============================================================================
[CmdletBinding()]
param(
    [int]$Port = 8000,
    [switch]$Reload
)

$ErrorActionPreference = "Stop"
$WorkspaceRoot = $PSScriptRoot
Set-Location $WorkspaceRoot

Write-Host "`n=== Launching OrderFlow Sentinel Backend ===" -ForegroundColor Cyan

# 1. Locate Python executable
$PythonExe = Join-Path $WorkspaceRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Host "[ERROR] Virtual environment not found at $PythonExe" -ForegroundColor Red
    Write-Host "Please create it using: python -m venv .venv" -ForegroundColor Yellow
    exit 1
}

# 2. Check if Port is already in use
$PortInUse = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($PortInUse) {
    Write-Host "[WARN] Port $Port is currently in use by process PID $($PortInUse.OwningProcess)" -ForegroundColor Yellow
    Write-Host "If this is an old Uvicorn instance, stop it with: Stop-Process -Id $($PortInUse.OwningProcess) -Force" -ForegroundColor Yellow
    Write-Host "Attempting to launch anyway...`n"
}

# 3. Check for compiled frontend
$DistPath = Join-Path $WorkspaceRoot "frontend\dist\index.html"
if (Test-Path $DistPath) {
    Write-Host "[INFO] Production frontend bundle detected in frontend\dist." -ForegroundColor Green
    Write-Host "[INFO] Dashboard UI will be available at: http://localhost:$Port/ui" -ForegroundColor Green
} else {
    Write-Host "[WARN] frontend\dist not found. Run .\build_frontend.ps1 if you wish to serve the UI on /ui." -ForegroundColor Yellow
}

Write-Host "[INFO] Swagger Docs: http://localhost:$Port/docs" -ForegroundColor Cyan
Write-Host "[INFO] Health Check: http://localhost:$Port/api/v1/health" -ForegroundColor Cyan
Write-Host "[INFO] Press Ctrl+C to stop the server.`n" -ForegroundColor White

$ArgsList = @("-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "$Port")
if ($Reload) {
    $ArgsList += "--reload"
}

& $PythonExe @ArgsList

