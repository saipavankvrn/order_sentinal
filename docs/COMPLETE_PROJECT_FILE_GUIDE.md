# OrderFlow Sentinel — Complete Project File & Folder Guide

> **Target Version**: 1.2.1-live-demo  
> **Platform**: FastAPI (Python 3.12) + React 18 (Vite + TypeScript) + SQLite (SQLAlchemy)  
> **Purpose**: A comprehensive, beginner-friendly reference for every single source file and directory in OrderFlow Sentinel.

---

## 1. Project Directory Structure Map

```text
Virtusa Jatayu/
├── .env                              # Local active environment variables (git-ignored)
├── .env.example                      # Safe template for environment variables
├── .gitignore                        # Git exclusion rules
├── .pytest_cache/                    # Pytest execution cache
├── .venv/                            # Python 3.12 virtual environment
├── .vscode/                          # Editor workspace settings
│   └── settings.json
├── backend/                          # FastAPI Backend Application
│   ├── requirements.txt              # Python production & test dependencies
│   ├── live_demo.py                  # CLI demonstration test script
│   ├── app/
│   │   ├── __init__.py               # Package marker
│   │   ├── main.py                   # FastAPI Application Entrypoint & SPA Mount
│   │   ├── ai/
│   │   │   ├── __init__.py
│   │   │   └── gemini_rca.py         # Google Gemini RCA & Deterministic Fallback Engine
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── router.py         # API V1 Master Router aggregator
│   │   │       └── endpoints/
│   │   │           ├── __init__.py
│   │   │           ├── analytics.py   # KPI metrics & failure distribution endpoints
│   │   │           ├── approvals.py   # Human-in-the-Loop approval queue endpoints
│   │   │           ├── audit.py       # Immutable audit event log query endpoints
│   │   │           ├── health.py      # Health & database connectivity check
│   │   │           ├── incidents.py   # Incident retrieval & lifecycle endpoints
│   │   │           ├── orders.py      # Order creation, listing & detail endpoints
│   │   │           ├── rca.py         # Root cause analysis report endpoints
│   │   │           ├── resolutions.py # Self-healing execution endpoints
│   │   │           └── simulation.py  # Demonstration scenarios & session reset
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py             # Pydantic Settings & environment config
│   │   │   └── logging.py            # Structured system logger
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── base.py               # SQLAlchemy declarative base
│   │   │   └── session.py            # SQLite engine, sessionmaker & WAL init
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── order.py              # 7 Core SQLAlchemy ORM Database Models
│   │   ├── policies/
│   │   │   ├── __init__.py
│   │   │   └── policy_engine.py      # Authoritative deterministic policy matrix
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── analytics.py          # Dashboard analytics Pydantic models
│   │   │   ├── approval.py           # Approval request & decision schemas
│   │   │   ├── audit.py              # Audit trail log schemas
│   │   │   ├── common.py             # Standard ApiResponse[T] wrapper
│   │   │   ├── incident.py           # Incident & RCA response schemas
│   │   │   ├── order.py              # Order & event request/response models
│   │   │   ├── resolution.py         # Self-healing action execution schemas
│   │   │   └── simulation.py         # Scenario execution & reset schemas
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── approval_service.py   # HITL approval business logic
│   │   │   ├── audit_service.py      # Immutable audit trail persistence
│   │   │   ├── detector.py           # Deterministic failure detector & incident creator
│   │   │   ├── order_service.py      # 7-stage order orchestrator & transitions
│   │   │   ├── resolution_service.py # Autonomous retry & backoff execution
│   │   │   └── simulator.py          # Downstream microservice failure simulator
│   │   └── static/
│   │       └── index.html            # Static fallback HTML
│   └── tests/                        # Backend Pytest Suite (53 Passing Tests)
│       ├── __init__.py
│       ├── conftest.py               # Isolated in-memory SQLite fixture
│       ├── test_analytics.py         # Analytics KPI endpoint tests
│       ├── test_health.py             # Server & DB health check tests
│       ├── test_live_demo.py         # Live demo scenarios & session reset tests
│       ├── test_milestone_4_frontend_integration.py # API & UI contract tests
│       ├── test_scenario_1.py        # HTTP 503 self-healing tests
│       ├── test_scenario_2.py        # Fulfilment SLA delay tests
│       └── test_scenario_3.py        # HTTP 422 HITL substitution tests
├── frontend/                         # React 18 + Vite + TypeScript Application
│   ├── index.html                    # Single Page Application HTML shell
│   ├── package.json                  # Frontend dependencies and npm scripts
│   ├── package-lock.json             # Exact dependency tree lockfile
│   ├── postcss.config.js             # PostCSS configuration for Tailwind
│   ├── tailwind.config.js            # Tailwind CSS styling design tokens
│   ├── tsconfig.json                 # TypeScript compiler configuration
│   ├── vite.config.ts                # Vite dev server and API proxy setup
│   ├── dist/                         # Compiled production bundle served by FastAPI
│   ├── tests/
│   │   ├── client_and_state.test.mjs # 9 Node native frontend unit tests
│   │   └── browser_e2e.mjs           # Browser Puppeteer smoke test
│   └── src/
│       ├── App.tsx                   # Top-level state coordinator & tab router
│       ├── index.css                 # Global CSS styles & Tailwind directives
│       ├── main.tsx                  # React DOM rendering root
│       ├── api/
│       │   └── client.ts             # Strongly-typed Axios/Fetch HTTP client
│       ├── components/
│       │   ├── common/
│       │   │   ├── Badge.tsx         # Color-coded status chip component
│       │   │   └── Card.tsx          # Consistent container card component
│       │   ├── layout/
│       │   │   ├── Header.tsx        # Application header, logo & live clock
│       │   │   └── Navigation.tsx    # 4-tab top navigation bar
│       │   ├── simulation/
│       │   │   └── SimulationControls.tsx # Quick-trigger scenario toolbar
│       │   └── views/
│       │       ├── ViewA_Dashboard.tsx       # KPI metrics & order list with pagination
│       │       ├── ViewB_JourneyRCA.tsx      # 7-stage visual timeline & RCA viewer
│       │       ├── ViewC_ApprovalsAudit.tsx  # HITL approval table & audit trail viewer
│       │       └── ViewD_LiveDemo.tsx        # Live test order cockpit & session reset
│       └── types/
│           └── index.ts              # Frontend TypeScript data interfaces
├── docs/                             # Project Architecture & Operational Guides
├── orderflow_sentinel.db             # Primary SQLite persistent database (WAL)
├── orderflow_sentinel.db-shm         # SQLite Shared Memory index file
├── orderflow_sentinel.db-wal         # SQLite Write-Ahead Log journal
├── build_frontend.ps1                # PowerShell script: TypeScript compile & Vite build
├── check_environment.ps1             # PowerShell script: Diagnostic prerequisite verification
├── run_backend.ps1                   # PowerShell script: Launch FastAPI via Uvicorn
├── run_frontend.ps1                  # PowerShell script: Launch Vite Dev Server
├── run_tests.ps1                     # PowerShell script: Execute full backend & frontend test suite
└── README.md                         # Project introduction & quick-start overview
```

---

## 2. Backend Files Detailed Guide

### `backend/app/main.py`
- **Exact Path**: `backend/app/main.py`
- **Purpose**: Central FastAPI application instance, lifespan lifecycle manager, middleware configuration, and Single Page Application (SPA) static file host.
- **Key Functions/Objects**:
  - `lifespan(app: FastAPI)`: Startup hook that initializes the SQLite database, verifies connectivity, and configures the Gemini AI client; logs shutdown events.
  - `app`: The instantiated `FastAPI` instance.
  - `read_dashboard_ui()`: Endpoint mapped to `GET /ui` that serves the compiled React `index.html`.
  - `read_root()`: Endpoint mapped to `GET /` that returns system health metadata and documentation URLs.
- **Inputs & Outputs**: Receives incoming HTTP requests; returns JSON API responses or HTML SPA content.
- **Dependencies**: Depends on `backend.app.core.config`, `backend.app.db.session`, and `backend.app.api.v1.router`.
- **Status**: **Essential**. The application will not boot without this file.

### `backend/app/core/config.py`
- **Exact Path**: `backend/app/core/config.py`
- **Purpose**: Defines application settings, environment variable parsing, and default fallback parameters using Pydantic Settings.
- **Key Classes**:
  - `Settings(BaseSettings)`: Validates `APP_NAME`, `API_V1_PREFIX`, `HOST`, `PORT`, `DATABASE_URL`, `GEMINI_API_KEY`, `GEMINI_MODEL_ID`, and `LOG_LEVEL`. Automatically loads from `.env`.
- **Dependencies**: Used by `main.py`, `session.py`, `gemini_rca.py`, and `logging.py`.
- **Status**: **Essential**.

### `backend/app/core/logging.py`
- **Exact Path**: `backend/app/core/logging.py`
- **Purpose**: Configures a unified, color-coded, structured log formatter.
- **Key Objects**:
  - `logger`: Root loguru/standard logger writing formatted timestamps, log levels, and messages.
- **Dependencies**: Used across all services, endpoints, and database modules.
- **Status**: **Essential**.

### `backend/app/db/session.py`
- **Exact Path**: `backend/app/db/session.py`
- **Purpose**: Configures SQLAlchemy SQLite engine, sessionmaker, WAL mode activation, and schema auto-migration.
- **Key Functions**:
  - `init_db()`: Executes `Base.metadata.create_all()` and inspects columns in `orders` (auto-adding `is_demo_order` and `demo_session_id` if missing).
  - `verify_database_connection()`: Runs `SELECT 1` to ensure SQLite is readable and writable.
  - `get_db()`: FastAPI dependency generator that provides a transactional database session per request and handles cleanup.
- **Status**: **Essential**.

### `backend/app/models/order.py`
- **Exact Path**: `backend/app/models/order.py`
- **Purpose**: SQLAlchemy ORM definitions representing the database tables.
- **Key Models**:
  - `Order`: Primary order record with customer info, amount, 7-stage status (`PENDING`, `PROCESSING`, `DELAYED`, `COMPLETED`, `FAILED`), and live demo indicators (`is_demo_order`, `demo_session_id`).
  - `OrderEvent`: Microsecond-accurate telemetry records for each hop (`VALIDATION`, `INVENTORY`, etc.) recording endpoint, HTTP status, and duration.
  - `Incident`: Formal failure records tracking category, severity, and retry attempts.
  - `RCAReport`: Root cause analysis records holding AI or deterministic findings, recommended action, and risk level.
  - `ResolutionAction`: Self-healing actions tracking idempotency key, retry count, and verification state.
  - `OperatorApproval`: Human approval records for Scenario 3 tracking candidate action, proposed parameters, and decision status (`PENDING`, `APPROVED`, `REJECTED`).
  - `AuditLog`: Immutable, append-only security and operational audit trail.
  - `SystemPolicy`: Configurable rules (e.g. stage SLA thresholds and max retry ceilings).
- **Status**: **Essential**.

### `backend/app/policies/policy_engine.py`
- **Exact Path**: `backend/app/policies/policy_engine.py`
- **Purpose**: Authoritative deterministic decision engine that evaluates recovery actions against strict system policies before execution.
- **Key Methods**:
  - `evaluate_action()`: Checks whether an action (e.g. `RETRY_WITH_BACKOFF`, `EXPEDITE_FULFILMENT`, `SUBSTITUTE_SKU_AND_REALLOCATE`) is permitted, prohibited, or requires human authorization.
  - Intercepts hard business rejections (HTTP 422) and blocks automated retry; blocks illegal auto-cancellations.
- **Status**: **Essential**. Protects against dangerous unverified actions.

### `backend/app/ai/gemini_rca.py`
- **Exact Path**: `backend/app/ai/gemini_rca.py`
- **Purpose**: Generates evidence-grounded advisory Root Cause Analysis (RCA) diagnoses.
- **Key Methods**:
  - `analyze_incident()`: Formulates structured telemetry prompts for the Gemini API (`gemini-flash-latest`).
  - `_generate_deterministic_fallback()`: Hardened deterministic rule-based diagnosis activated automatically if the API key is missing, network fails, or quota is exceeded.
- **Status**: **Essential**. Gemini is advisory only; the deterministic fallback guarantees 100% operational uptime.

### `backend/app/services/`
- **`order_service.py`**: Coordinates order creation and advances the order across the 7 journey stages (`VALIDATION` $\to$ `NOTIFICATION`).
- **`detector.py`**: Inspects event status and latency; detects HTTP 503, SLA breaches, and HTTP 422 rejections; creates incidents and triggers RCA.
- **`simulator.py`**: Injects synthetic failures (HTTP 503 at payment, artificial delay at fulfilment, HTTP 422 at inventory).
- **`resolution_service.py`**: Executes autonomous retries with backoff and unique idempotency keys; verifies downstream state before clearing incidents.
- **`approval_service.py`**: Manages the operator approval queue; validates substitution parameters; triggers inventory re-reservation.
- **`audit_service.py`**: Writes immutable audit log entries recording actor type (`SYSTEM`, `AI_AGENT`, `OPERATOR`) and timestamp.
- **Status**: **Essential**. These implement the core business logic.

### `backend/app/api/v1/endpoints/`
- **`orders.py`**: `GET /api/v1/orders`, `POST /api/v1/orders`, `GET /api/v1/orders/{id}`, `GET /api/v1/orders/{id}/events`.
- **`incidents.py`**: `GET /api/v1/incidents`, `GET /api/v1/incidents/{id}`.
- **`rca.py`**: `GET /api/v1/rca/{id}`, `GET /api/v1/rca/incident/{incident_id}`.
- **`resolutions.py`**: `POST /api/v1/resolutions/{id}/execute`.
- **`approvals.py`**: `GET /api/v1/approvals/pending`, `GET /api/v1/approvals/{id}`, `POST /api/v1/approvals/{id}/decide`.
- **`simulation.py`**: `POST /api/v1/simulation/trigger-scenario`, `POST /api/v1/simulation/reset-demo-session`.
- **`analytics.py`**: `GET /api/v1/analytics/metrics`, `GET /api/v1/analytics/failure-distribution`.
- **`audit.py`**: `GET /api/v1/audit/logs`.
- **`health.py`**: `GET /api/v1/health`.
- **Status**: **Essential**. Exposes all REST API contracts.

---

## 3. Frontend Files Detailed Guide

### `frontend/src/App.tsx`
- **Exact Path**: `frontend/src/App.tsx`
- **Purpose**: Main React component managing top-level state, active tab navigation, demo session ID generation, and deep-link synchronization.
- **Key State Variables**:
  - `activeTab`: Switches between `'dashboard'`, `'journey'`, `'approvals'`, and `'live-demo'`.
  - `selectedOrderId`: Tracks currently selected order for View B inspection.
  - `demoSessionId`: Persistent session ID (`demo-<timestamp>`) isolating live demonstration orders.
- **Status**: **Essential**. Root UI orchestrator.

### `frontend/src/api/client.ts`
- **Exact Path**: `frontend/src/api/client.ts`
- **Purpose**: Strongly-typed HTTP API client with centralized error handling and request wrapping.
- **Key Methods**:
  - `getOrders()`, `getOrder()`, `getOrderEvents()`, `getIncidents()`, `getRCA()`, `getPendingApprovals()`, `submitApprovalDecision()`, `getAnalyticsMetrics()`, `triggerScenario()`, `resetDemoSession()`.
- **Status**: **Essential**.

### `frontend/src/types/index.ts`
- **Exact Path**: `frontend/src/types/index.ts`
- **Purpose**: TypeScript interfaces defining all backend API contracts (`Order`, `OrderEvent`, `Incident`, `RCAReport`, `OperatorApproval`, `AuditLog`, `SimulationResponse`).
- **Status**: **Essential**. Ensures compile-time type safety.

### `frontend/src/components/views/`
- **`ViewA_Dashboard.tsx`**: KPI cards (Total Orders, Self-Healed, SLA Delayed, Pending Approvals), failure distribution chart, and paginated order table with demo filtering.
- **`ViewB_JourneyRCA.tsx`**: Visual 7-stage order progress stepper, raw telemetry event timeline, and structured Root Cause Analysis card.
- **`ViewC_ApprovalsAudit.tsx`**: Human approval review queue with parameter inputs (Substitute SKU, Alternate Hub) and searchable audit event trail.
- **`ViewD_LiveDemo.tsx`**: Live order demonstration cockpit featuring auto-generated order IDs, scenario selector, 🎲 Random Demo Mode, live telemetry streaming, and safe session reset.
- **Status**: **Essential**. These provide the 4 primary user interfaces.

---

## 4. Root PowerShell Scripts Guide

| Script | Purpose | Execution Command |
|---|---|---|
| [`run_backend.ps1`](file:///d:/Virtusa Jatayu/run_backend.ps1) | Boots FastAPI backend on `http://localhost:8000` via Uvicorn. | `powershell -ExecutionPolicy Bypass -File .\run_backend.ps1` |
| [`run_frontend.ps1`](file:///d:/Virtusa Jatayu/run_frontend.ps1) | Starts Vite frontend dev server on `http://localhost:3000`. | `powershell -ExecutionPolicy Bypass -File .\run_frontend.ps1` |
| [`run_tests.ps1`](file:///d:/Virtusa Jatayu/run_tests.ps1) | Executes 53 backend pytest tests and 9 frontend tests with DB isolation. | `powershell -ExecutionPolicy Bypass -File .\run_tests.ps1` |
| [`build_frontend.ps1`](file:///d:/Virtusa Jatayu/build_frontend.ps1) | Runs TypeScript linting and Vite build, generating `frontend/dist/`. | `powershell -ExecutionPolicy Bypass -File .\build_frontend.ps1` |
| [`check_environment.ps1`](file:///d:/Virtusa Jatayu/check_environment.ps1) | Validates Python, Node.js, SQLite DB, and `.env` prerequisites. | `powershell -ExecutionPolicy Bypass -File .\check_environment.ps1` |

