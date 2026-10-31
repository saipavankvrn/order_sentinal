# OrderFlow Sentinel — AI-Powered Self-Healing Order Failure Detection & Resolution Platform

**OrderFlow Sentinel** is an enterprise-grade order journey monitoring, deterministic failure detection, and automated self-healing platform engineered for the **Virtusa Jatayu Hackathon**.

Built as a **Modular Monolith with Simulated Downstream Logistics and Optional Gemini Advisory AI**, it monitors multi-hop e-commerce order journeys across 7 canonical stages, detects transient outages and SLA breaches deterministically, diagnoses probable root causes using ingested telemetry evidence, and executes safe recovery actions strictly governed by **Policy-as-Code**. High-risk operations and permanent business rejections are routed to an operator Human-in-the-Loop (HITL) approval queue.

---

## 1. Quick Start (Windows PowerShell)

OrderFlow Sentinel provides automated utility scripts for rapid verification and execution:

### 1. Check Environment & Prerequisites
```powershell
powershell -ExecutionPolicy Bypass -File .\check_environment.ps1
```
*(Verifies Python 3.12, Node.js v24, npm, SQLite database connection, and configuration).*

### 2. Run the Platform in Production-Style Mode (FastAPI + React SPA)
```powershell
# Compile the frontend SPA bundle
powershell -ExecutionPolicy Bypass -File .\build_frontend.ps1

# Launch the FastAPI backend server
powershell -ExecutionPolicy Bypass -File .\run_backend.ps1
```
Open your browser and navigate to: **`http://localhost:8000/ui`**

### 3. Run in Split Development Mode (Hot-Reloading)
- **Terminal 1 (Backend):**
  ```powershell
  .\run_backend.ps1 -Reload
  ```
- **Terminal 2 (Frontend Dev Server):**
  ```powershell
  .\run_frontend.ps1
  ```
Navigate to: **`http://localhost:3000`** *(API calls to `/api/v1/*` are automatically proxied to port 8000).*

### 4. Run the Full Regression Test Suite
```powershell
powershell -ExecutionPolicy Bypass -File .\run_tests.ps1
```
*(Executes 46 backend Pytest suites in an isolated temporary SQLite database and 9 frontend unit tests with zero persistent database mutations).*

---

## 2. Comprehensive Documentation Sitemap (`docs/`)

The repository includes complete technical handover documentation for all development, testing, and operational workflows:

| Guide | Link | Description |
|---|---|---|
| **Project Architecture Guide** | [`docs/PROJECT_ARCHITECTURE_GUIDE.md`](docs/PROJECT_ARCHITECTURE_GUIDE.md) | Full system design, Mermaid architecture & scenario state machine diagrams, folder-by-folder explanation, and module catalog. |
| **Setup & Configuration Guide** | [`docs/SETUP_AND_CONFIGURATION.md`](docs/SETUP_AND_CONFIGURATION.md) | Detailed manual setup steps for Python virtualenv, Node.js toolchains, environment variables, startup modes, and URLs. |
| **Scenario Workflow Guide** | [`docs/SCENARIO_WORKFLOW_GUIDE.md`](docs/SCENARIO_WORKFLOW_GUIDE.md) | Deep dive into Scenarios 0, 1, 2, and 3: triggers, detection, RCA, policy rules, verification, audit records, and final states. |
| **Manual Testing Guide** | [`docs/MANUAL_TESTING_GUIDE.md`](docs/MANUAL_TESTING_GUIDE.md) | Comprehensive manual QA test matrix (19 test cases), acceptance checklist, and expected verification criteria. |
| **API Testing Guide** | [`docs/API_TESTING_GUIDE.md`](docs/API_TESTING_GUIDE.md) | OpenAPI REST reference with safe PowerShell `Invoke-RestMethod` and `curl` request/response examples for all 14 endpoints. |
| **Troubleshooting Guide** | [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) | Detailed failure modes and fixes for environment paths, port collisions, SQLite locks, Gemini quotas, and UI rendering. |
| **Demonstration & Interview Guide** | [`docs/PROJECT_DEMONSTRATION_GUIDE.md`](docs/PROJECT_DEMONSTRATION_GUIDE.md) | 3-minute executive pitch, 5-minute live demo walkthrough, and 25 technical interview questions with deep answers. |

---

## 3. Technology Stack & Key Specifications

- **Backend:** Python 3.12.10, FastAPI 0.115+, SQLAlchemy 2.0, Pydantic v2, SQLite (Write-Ahead Logging mode enabled), Uvicorn.
- **Frontend:** React 18.3, TypeScript 5.6, Vite 5.4, Tailwind CSS 3.4, Lucide Icons, Recharts 2.13.
- **AI Advisory Engine:** Google GenAI SDK (`google-genai` 1.0+), configured with `gemini-2.0-flash` and an automatic offline deterministic fallback engine.
- **Testing:** Pytest 8.4, HTTPX / FastAPI TestClient, Node.js Native Test Runner (`node --test`), Chrome DevTools Protocol (CDP) headless automation.

---

## 4. Key Application Endpoints

- **Operator Dashboard UI:** [`http://localhost:8000/ui`](http://localhost:8000/ui)
- **Interactive OpenAPI Swagger Docs:** [`http://localhost:8000/docs`](http://localhost:8000/docs)
- **Alternative ReDoc UI:** [`http://localhost:8000/redoc`](http://localhost:8000/redoc)
- **System Health Check:** [`http://localhost:8000/api/v1/health`](http://localhost:8000/api/v1/health)
- **Analytics Metrics:** [`http://localhost:8000/api/v1/analytics/metrics`](http://localhost:8000/api/v1/analytics/metrics)
- **Pending Human Approvals:** [`http://localhost:8000/api/v1/approvals/pending`](http://localhost:8000/api/v1/approvals/pending)
- **Immutable Audit Trail:** [`http://localhost:8000/api/v1/audit`](http://localhost:8000/api/v1/audit)

---

## 5. Architectural Principles & Safety Invariants

1. **AI is Strictly Advisory:** Google Gemini produces root cause narratives and recovery proposals. The LLM possesses zero permissions to alter database states or trigger order mutations directly.
2. **Deterministic Policy Boundary:** Every candidate recovery action must pass the Policy Engine. Unconstrained retries are capped at 3, blind payment retries are strictly prohibited, destructive order cancellations are vetoed, and permanent out-of-stock rejections require human operator authorization.
3. **Downstream State Verification:** Recovery is never declared based solely on an HTTP 200 return code. The system actively queries downstream service state to confirm that physical reservations or allocations exist before declaring recovery.
4. **Append-Only Immutable Audit Trail:** Every automated action, AI diagnosis, policy evaluation, and operator decision is recorded in the `audit_logs` table with actor classification and timestamps. Records cannot be edited or deleted via the API.
"# order_sentinal" 
