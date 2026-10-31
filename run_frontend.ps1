# ==============================================================================
# OrderFlow Sentinel - Launch Vite Frontend Development Server
# ==============================================================================
[CmdletBinding()]
param(
    [int]$Port = 3000
)

$ErrorActionPreference = "Stop"
$WorkspaceRoot = $PSScriptRoot
Set-Location (Join-Path $WorkspaceRoot "frontend")

Write-Host "`n=== Launching OrderFlow Sentinel Frontend Development Server ===" -ForegroundColor Cyan

# Prepend WinGet Node path if present
$NodePath = "C:\Users\Asus\AppData\Local\Microsoft\WinGet\Packages\OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe\node-v24.20.0-win-x64"
if (Test-Path $NodePath) {
    $env:Path = "$NodePath;" + $env:Path
}

Write-Host "[INFO] Vite Dev Server: http://localhost:$Port" -ForegroundColor Green
Write-Host "[INFO] Backend API Proxy: http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "[NOTE] Ensure the backend server is running via .\run_backend.ps1 in another terminal." -ForegroundColor Yellow
Write-Host "[INFO] Press Ctrl+C to stop the development server.`n" -ForegroundColor White

& npm.cmd run dev -- --port $Port
Set-Location $WorkspaceRoot

