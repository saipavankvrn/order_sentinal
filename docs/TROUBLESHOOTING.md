# OrderFlow Sentinel — Comprehensive Troubleshooting Guide

**Document Version:** 1.2.1  
**Operating System:** Windows 10 / Windows 11  
**Target Audience:** Forward Deployed Engineers, Support Engineers, Evaluators  

> [!CAUTION]
> **Data Integrity Rule:** Never delete, truncate, or reset the persistent SQLite database (`orderflow_sentinel.db`) as a troubleshooting remedy. Database locks and state mismatches can always be safely diagnosed and resolved without data destruction.

---

## 1. Environment & Process Issues

### 1.1 Python Command Not Recognized / WindowsApps Alias Error
- **Likely Cause:** Windows App Execution Alias intercepts `python` and points to an uninstalled Microsoft Store placeholder or sandboxed path.
- **Diagnosis:**
  ```powershell
  where.exe python
  # Outputs: C:\Users\<User>\AppData\Local\Microsoft\WindowsApps\python.exe
  ```
- **Safe Fix:**
  Use the virtual environment's explicit Python binary directly:
  ```powershell
  & "D:\Virtusa Jatayu\.venv\Scripts\python.exe" --version
  ```
  Or disable the app alias in Windows Settings: *Manage App Execution Aliases* $\rightarrow$ Disable `python.exe` and `python3.exe`.
- **Verification:**
  ```powershell
  .\.venv\Scripts\python.exe -c "import sys; print(sys.version)"
  ```

---

### 1.2 Node.js or npm Command Not Recognized
- **Likely Cause:** Node.js was installed via WinGet into a non-standard User path not yet present in your PowerShell `$env:Path`.
- **Diagnosis:**
  ```powershell
  Get-Command node -ErrorAction SilentlyContinue
  # Returns nothing
  ```
- **Safe Fix:**
  Prepend the known WinGet Node.js LTS path to your current session `$env:Path`:
  ```powershell
  $nodeDir = "C:\Users\Asus\AppData\Local\Microsoft\WinGet\Packages\OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe\node-v24.20.0-win-x64"
  if (Test-Path $nodeDir) {
      $env:Path = "$nodeDir;" + $env:Path
  }
  ```
- **Verification:**
  ```powershell
  node -v; npm.cmd -v
  # Should report v24.20.0 and 11.19.0
  ```

---

### 1.3 Port 8000 Already Occupied
- **Likely Cause:** A previous instance of Uvicorn is still running in the background.
- **Diagnosis:**
  ```powershell
  Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
  ```
- **Safe Fix:**
  Find the PID and terminate the zombie process:
  ```powershell
  $procId = (Get-NetTCPConnection -LocalPort 8000 -State Listen).OwningProcess
  if ($procId) { Stop-Process -Id $procId -Force }
  ```
- **Verification:**
  ```powershell
  Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
  # Should return empty
  ```

---

### 1.4 Port 3000 (or 5173) Already Occupied
- **Likely Cause:** Vite dev server was left running.
- **Diagnosis:**
  ```powershell
  Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue
  ```
- **Safe Fix:**
  Terminate the process holding port 3000:
  ```powershell
  $p = (Get-NetTCPConnection -LocalPort 3000 -State Listen).OwningProcess
  if ($p) { Stop-Process -Id $p -Force }
  ```
- **Verification:**
  Port is available for `npm run dev`.

---

## 2. Database & Persistence Issues

### 2.1 SQLite Database Lock (`database is locked`)
- **Likely Cause:** Multiple processes attempting write operations while WAL mode is disabled, or a previous uncommitted transaction held an exclusive lock.
- **Diagnosis:**
  Check WAL mode via SQLite:
  ```powershell
  .\.venv\Scripts\python.exe -c "
  import sqlite3
  conn = sqlite3.connect('orderflow_sentinel.db')
  print('Journal mode:', conn.execute('PRAGMA journal_mode').fetchone()[0])
  "
  ```
- **Safe Fix:**
  Enable Write-Ahead Logging (`WAL`) mode, which allows unlimited concurrent readers alongside a concurrent writer:
  ```powershell
  .\.venv\Scripts\python.exe -c "
  import sqlite3
  conn = sqlite3.connect('orderflow_sentinel.db')
  conn.execute('PRAGMA journal_mode=WAL;')
  conn.commit()
  print('WAL mode confirmed!')
  "
  ```
- **Verification:**
  Run `pytest backend/tests/test_health.py` to confirm database connectivity.

---

### 2.2 Database Connection Errors on Startup
- **Likely Cause:** Incorrect `DATABASE_URL` in `.env` (e.g. wrong slashes or invalid path).
- **Diagnosis:**
  Check `DATABASE_URL` in `.env`.
- **Safe Fix:**
  Set `DATABASE_URL=sqlite:///./orderflow_sentinel.db` in `.env`. The 3 slashes indicate relative path from workspace root.
- **Verification:**
  Run `Invoke-RestMethod -Uri "http://localhost:8000/api/v1/health"`.

---

## 3. AI & Gemini Integration Issues

### 3.1 Missing Gemini API Key (`GEMINI_API_KEY`)
- **Likely Cause:** `GEMINI_API_KEY` is commented out or omitted from `.env`.
- **Diagnosis:**
  Check `/api/v1/health`. `ai_engine.gemini_available` is `false`, `fallback_mode` is `true`.
- **Safe Fix:**
  **This is normal and fully supported.** The system operates 100% reliably in deterministic fallback mode. If you wish to enable live Gemini LLM diagnosis, obtain a free API key from Google AI Studio (`https://aistudio.google.com/`) and set `GEMINI_API_KEY=your_key` in `.env`.
- **Verification:**
  Restart backend and check terminal startup logs: `Gemini API configured with model: gemini-2.0-flash`.

---

### 3.2 Gemini API Quota Exhausted / Rate Limited (HTTP 429)
- **Likely Cause:** Google AI Studio free tier RPM/TPM quota exceeded.
- **Diagnosis:**
  Application log displays: `Gemini RCA call failed (429 Resource Exhausted). Activating deterministic fallback.`
- **Safe Fix:**
  No manual intervention required. The `gemini_rca.py` engine catches the exception automatically and falls back to the internal deterministic rule engine.
- **Verification:**
  View B RCA card displays: `Model Source: DETERMINISTIC_FALLBACK` with identical policy recommendations.

---

### 3.3 Gemini API Timeout or Network Outage
- **Likely Cause:** Egress internet access blocked, proxy restriction, or Google API latency.
- **Diagnosis:**
  Log reports timeout on `client.models.generate_content`.
- **Safe Fix:**
  The engine automatically catches network errors and returns the deterministic fallback RCA within milliseconds. The user experience remains uninterrupted.

---

## 4. Frontend & User Interface Issues

### 4.1 Blank Dashboard or UI Not Loading
- **Likely Cause:** Compiled production assets in `frontend/dist/` are missing or outdated.
- **Diagnosis:**
  Check if `frontend/dist/index.html` exists.
- **Safe Fix:**
  Recompile the frontend:
  ```powershell
  cd "D:\Virtusa Jatayu\frontend"
  npm.cmd run build
  cd ..
  ```
- **Verification:**
  Navigate to `http://localhost:8000/ui` in Google Chrome.

---

### 4.2 Orders Not Loading / Spinner Keeps Spinning
- **Likely Cause:** Backend server is not running on port 8000, or browser hit an unexpected CORS block.
- **Diagnosis:**
  Open Chrome DevTools (F12) $\rightarrow$ Console / Network tab. Check for `ERR_CONNECTION_REFUSED`.
- **Safe Fix:**
  Start or restart the FastAPI backend server:
  ```powershell
  .\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
  ```
- **Verification:**
  Network tab displays `GET /api/v1/orders` returning HTTP 200.

---

### 4.3 "Inspect Journey" Shows Blank Screen for Orders on Later Pages
- **Likely Cause:** Previous bug DEF-02 (now fixed).
- **Diagnosis:**
  In `App.tsx`, active order is now fetched directly via `api.getOrder(orderId)`.
- **Safe Fix:**
  Ensure latest `App.tsx` and `ViewB_JourneyRCA.tsx` are built with `npm run build`.
- **Verification:**
  Navigate directly to `http://localhost:8000/ui?tab=journey&order_id=ORD-E27210FA` and confirm the 7-stage timeline renders immediately.

---

### 4.4 Telemetry Drawer Shows "0 Raw Events"
- **Likely Cause:** Previous schema naming mismatch DEF-04 (now fixed).
- **Diagnosis:**
  Check whether `raw_events` or `telemetry_events` are populated in `api/client.ts`.
- **Safe Fix:**
  `client.ts` normalizes `raw_events` into `telemetry_events`. Confirm latest frontend build is deployed.
- **Verification:**
  Click "View Telemetry Logs" in View B and verify JSON logs are rendered.

---

### 4.5 Approval Form Submission Fails with Error
- **Likely Cause:** Submitting approval with empty substitute SKU or warehouse hub.
- **Diagnosis:**
  Backend returns `HTTP 400: Substitute SKU is required for approval.`
- **Safe Fix:**
  Enter valid strings into both input fields (e.g. SKU: `SKU-CYBER-500-ALT`, Hub: `HUB-EAST-02`).
- **Verification:**
  Submitting the form triggers a green "Operator Decision Verified & Dispatched" banner.

---

### 4.6 Frontend Build Fails (`tsc && vite build`)
- **Likely Cause:** Node module version mismatch or TypeScript compiler error.
- **Diagnosis:**
  Inspect terminal output of `npm.cmd run build`.
- **Safe Fix:**
  Run typecheck and clean install:
  ```powershell
  cd "D:\Virtusa Jatayu\frontend"
  npm.cmd run lint
  npm.cmd run build
  cd ..
  ```
- **Verification:**
  Build outputs `dist/index.html` and `dist/assets/*.js`.

