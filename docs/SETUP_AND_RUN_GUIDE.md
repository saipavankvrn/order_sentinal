# OrderFlow Sentinel — Setup, Installation & Running Guide

> **Operating System**: Windows 11 (PowerShell)  
> **Backend**: Python 3.12 (FastAPI, SQLAlchemy, Uvicorn)  
> **Frontend**: Node.js v24.20.0 (React 18, Vite, TypeScript)  
> **Database**: SQLite with Write-Ahead Logging (WAL)  

---

## 1. Prerequisites Verification

Before starting, open a PowerShell terminal and confirm your installed tools:

```powershell
# Check Python version (Must be 3.12.x)
python --version

# Check Node.js and npm versions (Must be Node 20+ and npm 10+)
node -v
npm.cmd -v
```

> [!NOTE]  
> If PowerShell warns that running scripts is disabled (`PSSecurityException`), use `npm.cmd` instead of bare `npm`, or set the session execution policy using:  
> `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

You can also run our automated diagnostic script from the project root:
```powershell
Set-Location "d:\Virtusa Jatayu"
powershell -ExecutionPolicy Bypass -File .\check_environment.ps1
```

---

## 2. Step-by-Step Installation

### Step A: Backend Setup & Virtual Environment

1. Navigate to the project root directory:
   ```powershell
   Set-Location "d:\Virtusa Jatayu"
   ```

2. Create a Python 3.12 virtual environment (if not already present):
   ```powershell
   python -m venv .venv
   ```

3. Activate the virtual environment:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

4. Install the backend Python dependencies:
   ```powershell
   python -m pip install --upgrade pip
   pip install -r backend/requirements.txt
   ```

### Step B: Frontend Setup & Dependency Installation

1. Navigate to the `frontend` directory:
   ```powershell
   Set-Location "d:\Virtusa Jatayu\frontend"
   ```

2. Install Node modules:
   ```powershell
   npm.cmd install
   ```

3. Return to the project root:
   ```powershell
   Set-Location "d:\Virtusa Jatayu"
   ```

### Step C: Environment Configuration

1. Copy `.env.example` to `.env`:
   ```powershell
   Copy-Item .env.example .env
   ```

2. Inspect or edit `.env` in your text editor:
   ```ini
   APP_NAME=OrderFlow Sentinel
   APP_ENV=development
   API_V1_PREFIX=/api/v1
   HOST=0.0.0.0
   PORT=8000
   DEBUG=true
   DATABASE_URL=sqlite:///./orderflow_sentinel.db
   GEMINI_API_KEY=your_gemini_api_key_here
   GEMINI_MODEL_ID=gemini-flash-latest
   LOG_LEVEL=INFO
   ```
   *(Note: `GEMINI_API_KEY` is optional. If left as `your_gemini_api_key_here` or omitted, the application automatically runs in deterministic fallback mode).*

### Step D: Database Initialization

The database initializes automatically on backend startup. You do not need to run manual SQL migration scripts. On startup, [`backend/app/db/session.py`](file:///d:/Virtusa Jatayu/backend/app/db/session.py) creates all tables and auto-migrates any new columns.

---

## 3. Starting the Application

You have two supported ways to run OrderFlow Sentinel:

### Method 1: Single-Server Production Mode (FastAPI serves both API and React SPA)

This is the cleanest mode for demonstrations because it only requires **one terminal window**:

1. Compile the React frontend into static assets:
   ```powershell
   Set-Location "d:\Virtusa Jatayu"
   powershell -ExecutionPolicy Bypass -File .\build_frontend.ps1
   ```
   *This generates the production bundle inside `frontend/dist/`.*

2. Launch the backend server:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\run_backend.ps1
   ```
   *(Or run directly: `.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload`)*

3. Open your browser:
   - **Dashboard & UI**: [http://localhost:8000/ui](http://localhost:8000/ui)
   - **Interactive API Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Health Check**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

### Method 2: Development Mode (Vite Hot-Reloading + FastAPI Backend)

Use this mode if you plan to edit the React TypeScript code in real time:

#### Terminal 1 (Backend API):
```powershell
Set-Location "d:\Virtusa Jatayu"
powershell -ExecutionPolicy Bypass -File .\run_backend.ps1
```

#### Terminal 2 (Frontend Dev Server):
```powershell
Set-Location "d:\Virtusa Jatayu"
powershell -ExecutionPolicy Bypass -File .\run_frontend.ps1
```
*(Or navigate to `frontend` and run: `npm.cmd run dev -- --port 3000`)*

- **Vite Frontend**: [http://localhost:3000](http://localhost:3000)
  *(Vite automatically proxies all `/api` calls to the backend on `http://127.0.0.1:8000`)*.

---

## 4. Stopping and Restarting the Servers

### How to Stop:
- In either terminal window, press `Ctrl + C`.

### Force-Stopping if a Port is Blocked:
If a previous Uvicorn or Node process continues holding Port 8000 or Port 3000 in the background:

```powershell
# Check what is using Port 8000
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object LocalPort, OwningProcess

# Terminate the blocking process
Stop-Process -Id <PID> -Force
```

---

## 5. Running the Automated Regression Test Suite

Always execute the regression test suite before and after any code changes:

```powershell
Set-Location "d:\Virtusa Jatayu"
powershell -ExecutionPolicy Bypass -File .\run_tests.ps1
```

**What this verifies:**
1. Records persistent database order count (513 historical orders).
2. Executes **53 backend integration and scenario tests** using an isolated temporary SQLite database.
3. Confirms persistent database count is unchanged (0 synthetic test leaks).
4. Executes **9 frontend unit tests** verifying API error handling, parameter validation, and 7-stage status mappings.

