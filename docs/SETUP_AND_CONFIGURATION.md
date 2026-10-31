# OrderFlow Sentinel — Complete Setup & Configuration Guide

**Document Version:** 1.2.1  
**Target Platform:** Windows 10 / Windows 11 (PowerShell)  
**Primary Execution Root:** `D:\Virtusa Jatayu`  

---

## 1. Prerequisites & Environment Specifications

Before running OrderFlow Sentinel, ensure your development environment satisfies these requirements:

| Component | Minimum Version | Verified Version in Repo | Purpose |
|---|---|---|---|
| **Operating System** | Windows 10 (64-bit) | Windows 11 Pro 64-bit | Execution OS |
| **Python** | 3.10+ | **Python 3.12.10** | Backend runtime & test suite |
| **Node.js** | 18.0.0+ | **Node.js v24.20.0 LTS** | Frontend build & test toolchain |
| **npm** | 9.0.0+ | **npm 11.19.0** | Package manager for frontend |
| **Database** | SQLite 3.35+ | SQLite 3 with WAL support | Persistent local datastore (`orderflow_sentinel.db`) |
| **Browser** | Modern Chromium | Google Chrome 120+ | Interactive dashboard & CDP automation |

> [!NOTE]
> If Node.js and npm are installed via Windows Package Manager (`winget`), the binary path is typically located at:  
> `C:\Users\<User>\AppData\Local\Microsoft\WinGet\Packages\OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe\node-v24.20.0-win-x64`

---

## 2. Dependency Manifests

OrderFlow Sentinel maintains explicit dependency manifests for both backend and frontend:

### Backend Manifest: [`backend/requirements.txt`](file:///d:/Virtusa%20Jatayu/backend/requirements.txt)
```text
fastapi>=0.115.0,<1.0.0
uvicorn[standard]>=0.32.0,<1.0.0
pydantic>=2.9.0,<3.0.0
pydantic-settings>=2.6.0,<3.0.0
sqlalchemy>=2.0.36,<3.0.0
pytest>=8.3.0,<9.0.0
httpx>=0.28.0,<1.0.0
google-genai>=1.0.0,<2.0.0
```

### Frontend Manifest: [`frontend/package.json`](file:///d:/Virtusa%20Jatayu/frontend/package.json)
- **Core Dependencies:** `react@^18.3.1`, `react-dom@^18.3.1`, `lucide-react@^0.460.0`, `recharts@^2.13.3`.
- **Development Tooling:** `vite@^5.4.11`, `typescript@^5.6.3`, `tailwindcss@^3.4.15`, `@vitejs/plugin-react@^4.3.3`.

---

## 3. Step-by-Step Manual Setup

### Step 1: Open Terminal in Project Root
Launch PowerShell and change into the project root directory:
```powershell
cd "D:\Virtusa Jatayu"
```

### Step 2: Configure Windows PowerShell Script Execution Policy
Windows restricts PowerShell script execution by default. Allow script execution for your current session:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
```

### Step 3: Set Up Python Virtual Environment
Verify or create the Python virtual environment:
```powershell
# Create .venv if it does not exist
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1
```
*(Verify prompt prefix displays `(.venv)`).*

### Step 4: Install Backend Dependencies
Upgrade `pip` and install all required Python packages:
```powershell
python -m pip install --upgrade pip
pip install -r backend\requirements.txt
```

### Step 5: Environment File Configuration
The repository includes [`.env.example`](file:///d:/Virtusa%20Jatayu/.env.example). Copy it to `.env` if `.env` does not already exist:
```powershell
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}
```

Verify your `.env` contains:
```ini
APP_NAME=OrderFlow Sentinel
APP_ENV=development
API_V1_PREFIX=/api/v1
HOST=0.0.0.0
PORT=8000
DEBUG=true
DATABASE_URL=sqlite:///./orderflow_sentinel.db
# Optional: GEMINI_API_KEY=your_key_here
GEMINI_MODEL_ID=gemini-2.0-flash
LOG_LEVEL=INFO
```

### Step 6: Install Frontend Dependencies
```powershell
cd "D:\Virtusa Jatayu\frontend"
npm.cmd install
cd ..
```

---

## 4. Startup Modes

You can run OrderFlow Sentinel in either of two supported operational modes:

### Mode 1: Production-Style Single-Process Mode (Recommended for Demos)
In this mode, the React frontend is compiled into static assets (`frontend/dist/`), and FastAPI serves both the REST API and the complete Single-Page Application on port 8000.

1. **Build the Frontend Assets:**
   ```powershell
   cd "D:\Virtusa Jatayu\frontend"
   npm.cmd run build
   cd ..
   ```
   *(Creates `frontend/dist/index.html` and `frontend/dist/assets/`).*

2. **Start the FastAPI Backend Server:**
   ```powershell
   .\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
   ```

3. **Access the Dashboard:**
   Open your browser and navigate to:
   ```text
   http://localhost:8000/ui
   ```

---

### Mode 2: Split Development Mode (Hot-Reloading for Development)
In this mode, the backend runs on port 8000 and the Vite development server runs on port 3000 with live hot-module reloading and automatic proxying of `/api` requests.

1. **Start Backend Server (Terminal 1):**
   ```powershell
   cd "D:\Virtusa Jatayu"
   .\.venv\Scripts\Activate.ps1
   python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

2. **Start Frontend Dev Server (Terminal 2):**
   ```powershell
   cd "D:\Virtusa Jatayu\frontend"
   npm.cmd run dev
   ```

3. **Access the Dashboard:**
   Open your browser and navigate to:
   ```text
   http://localhost:3000
   ```
   *(All API calls to `/api/v1/*` are automatically proxied to `http://localhost:8000/api/v1/*`).*

---

## 5. Application URLs Reference

Once the application is running, the following endpoints are available:

| Resource | URL | Description |
|---|---|---|
| **Operator Dashboard UI** | `http://localhost:8000/ui` | Unified 3-view React operator console |
| **Interactive Swagger Docs** | `http://localhost:8000/docs` | OpenAPI 3.0 interactive Swagger testing console |
| **Alternative ReDoc UI** | `http://localhost:8000/redoc` | Clean, searchable technical API documentation |
| **System Health Check** | `http://localhost:8000/api/v1/health` | SQLite connectivity, WAL mode, and AI engine status |
| **Service Root Info** | `http://localhost:8000/` | Service metadata, active version (1.2.1), and entry links |
| **Analytics Metrics** | `http://localhost:8000/api/v1/analytics/metrics` | Ingested, completed, delayed, and pending counts |
| **Pending Approvals Queue** | `http://localhost:8000/api/v1/approvals/pending` | Awaiting Human-in-the-Loop decision list |
| **Immutable Audit Trail** | `http://localhost:8000/api/v1/audit` | Append-only security and operational audit records |
| **Orders API** | `http://localhost:8000/api/v1/orders` | Paginated order list (`skip`, `page`, `limit`) |

---

## 6. Verifying System Health

To confirm that the database is connected and WAL mode is active, execute:
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/health" -Method Get | ConvertTo-Json -Depth 4
```

Expected response:
```json
{
  "success": true,
  "data": {
    "status": "HEALTHY",
    "database": {
      "status": "CONNECTED",
      "engine": "sqlite",
      "wal_mode": true
    },
    "ai_engine": {
      "gemini_available": false,
      "model_configured": "gemini-2.0-flash",
      "fallback_mode": true
    },
    "uptime_seconds": 12
  },
  "message": "System is healthy and operational"
}
```
*(Notice: Even when `GEMINI_API_KEY` is omitted, the system reports `status: "HEALTHY"` with `fallback_mode: true`).*

