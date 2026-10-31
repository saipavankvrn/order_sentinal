# ==============================================================================
# OrderFlow Sentinel - Build Frontend Production Bundle
# ==============================================================================
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$WorkspaceRoot = $PSScriptRoot
Set-Location (Join-Path $WorkspaceRoot "frontend")

Write-Host "`n=== Building OrderFlow Sentinel Production Frontend ===" -ForegroundColor Cyan

# Prepend WinGet Node path if present
$NodePath = "C:\Users\Asus\AppData\Local\Microsoft\WinGet\Packages\OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe\node-v24.20.0-win-x64"
if (Test-Path $NodePath) {
    $env:Path = "$NodePath;" + $env:Path
}

Write-Host "[1/2] Running TypeScript Typecheck..." -ForegroundColor Cyan
& npm.cmd run lint
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] TypeScript typecheck failed!" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "[2/2] Compiling Production Bundle via Vite..." -ForegroundColor Cyan
& npm.cmd run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Vite production build failed!" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "`n[SUCCESS] Frontend build completed successfully!" -ForegroundColor Green
Write-Host "Compiled distribution bundle is ready in frontend\dist." -ForegroundColor Green
Write-Host "Start the backend via .\run_backend.ps1 to access http://localhost:8000/ui`n" -ForegroundColor White
Set-Location $WorkspaceRoot

