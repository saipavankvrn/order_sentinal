# OrderFlow Sentinel — Complete Developer Handover Report

> **Project**: OrderFlow Sentinel — AI-Powered Self-Healing Order Failure Detection and Resolution Platform  
> **Document Version**: 1.2.1-live-demo (Handover Edition)  
> **Target Audience**: Developer, Engineering Evaluator, Hackathon Judges  
> **Status**: Verified, Production-Ready, 100% Test Suite Pass  

---

## 1. What the Project Does

OrderFlow Sentinel is a **resilient, self-healing e-commerce order processing platform**. In high-volume e-commerce systems, an order hops across multiple independent microservices: Address Validation, Inventory, Payment, Fraud Check, Warehouse Fulfilment, Delivery Carrier, and Customer Notification.

When downstream microservices fail, Sentinel prevents order abandonment by:
1. **Detecting Failures Deterministically**: Flags transient failures (HTTP 503), permanent business rejections (HTTP 422 Out-of-Stock), and latency SLA threshold breaches (>5000ms).
2. **Generating Advisory Root Cause Analysis (RCA)**: Leverages Google Gemini (`gemini-flash-latest`) to produce structured root-cause findings with an instant, autonomous fallback to internal deterministic domain rules if Gemini is offline.
3. **Enforcing Policy-as-Code**: Prohibits dangerous actions (like duplicate retries on hard rejections or automatic cancellations) via an authoritative `PolicyEngine`.
4. **Self-Healing Autonomously**: Executes exponential backoff retries with cryptographic idempotency keys for transient errors.
5. **Facilitating Human-in-the-Loop Decisions**: Provides an interactive approval queue for business rejections where human operators authorize alternate inventory hubs or substitute SKUs.
6. **Verifying Downstream State**: Confirms verified state changes (e.g. `CHARGE_CAPTURED` or `INVENTORY_RESERVED`) before clearing incidents.
7. **Maintaining an Immutable Audit Trail**: Records append-only event logs tracking every system, AI agent, and operator action.

---

## 2. Recommended Reading & Learning Order

To master the codebase efficiently before your presentation, read the documentation files in this exact order:

```mermaid
flowchart LR
    Step1["1. docs/COMPLETE_PROJECT_FILE_GUIDE.md<br/>(Understand every file & folder)"] --> Step2["2. docs/PROJECT_ARCHITECTURE_EXPLANATION.md<br/>(Master the 6 Mermaid diagrams)"]
    Step2 --> Step3["3. docs/SCENARIO_WORKFLOW_EXPLANATION.md<br/>(Deep dive into Scenarios 0-3)"]
    Step3 --> Step4["4. docs/SETUP_AND_RUN_GUIDE.md<br/>(Boot the backend and frontend)"]
    Step4 --> Step5["5. docs/MANUAL_TESTING_GUIDE.md<br/>(Run the test cases in View D)"]
    Step5 --> Step6["6. docs/PROJECT_TECHNICAL_QA.md<br/>(Review the 42 technical interview Q&As)"]
```

1. [`docs/COMPLETE_PROJECT_FILE_GUIDE.md`](file:///d:/Virtusa Jatayu/docs/COMPLETE_PROJECT_FILE_GUIDE.md): File-by-file breakdown of backend and frontend.
2. [`docs/PROJECT_ARCHITECTURE_EXPLANATION.md`](file:///d:/Virtusa Jatayu/docs/PROJECT_ARCHITECTURE_EXPLANATION.md): Complete architecture, state machine, and data flow diagrams.
3. [`docs/SCENARIO_WORKFLOW_EXPLANATION.md`](file:///d:/Virtusa Jatayu/docs/SCENARIO_WORKFLOW_EXPLANATION.md): Technical lifecycle of Scenarios 0, 1, 2, and 3.
4. [`docs/SETUP_AND_RUN_GUIDE.md`](file:///d:/Virtusa Jatayu/docs/SETUP_AND_RUN_GUIDE.md): Verified Windows 11 installation and startup commands.
5. [`docs/ENVIRONMENT_AND_API_CONFIGURATION.md`](file:///d:/Virtusa Jatayu/docs/ENVIRONMENT_AND_API_CONFIGURATION.md): Environment settings and Gemini configuration.
6. [`docs/API_EXPLANATION_AND_TESTING.md`](file:///d:/Virtusa Jatayu/docs/API_EXPLANATION_AND_TESTING.md): REST endpoint reference and Swagger UI guide.
7. [`docs/DATABASE_EXPLANATION.md`](file:///d:/Virtusa Jatayu/docs/DATABASE_EXPLANATION.md): SQLite WAL concurrency and data model reference.
8. [`docs/MANUAL_TESTING_GUIDE.md`](file:///d:/Virtusa Jatayu/docs/MANUAL_TESTING_GUIDE.md): Automated tests and step-by-step QA verification scripts.
9. [`docs/TROUBLESHOOTING_GUIDE.md`](file:///d:/Virtusa Jatayu/docs/TROUBLESHOOTING_GUIDE.md): Fast solutions for ports, locks, and network errors.
10. [`docs/PROJECT_TECHNICAL_QA.md`](file:///d:/Virtusa Jatayu/docs/PROJECT_TECHNICAL_QA.md): 42 deep technical questions and answers for technical evaluation.

---

## 3. How to Install & Run the Project

### Verified Prerequisites:
- Windows 11 with PowerShell.
- Python 3.12 (`python --version`).
- Node.js v24+ and npm 10+ (`node -v`, `npm.cmd -v`).

### 1-Minute Startup (Production Single-Server Mode):
```powershell
Set-Location "d:\Virtusa Jatayu"

# 1. Run diagnostic check
powershell -ExecutionPolicy Bypass -File .\check_environment.ps1

# 2. Build the React frontend into static assets
powershell -ExecutionPolicy Bypass -File .\build_frontend.ps1

# 3. Launch FastAPI backend (serves both API & React UI)
powershell -ExecutionPolicy Bypass -File .\run_backend.ps1
```

### URLs:
- **Operator Dashboard**: [http://localhost:8000/ui](http://localhost:8000/ui)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

## 4. How to Test the Project

Execute the automated regression runner from the workspace root:
```powershell
Set-Location "d:\Virtusa Jatayu"
powershell -ExecutionPolicy Bypass -File .\run_tests.ps1
```

**Verification Results:**
- **53 Backend Pytest Tests**: **100% Passed** (health, orders, analytics, live demo, scenarios 1, 2, 3).
- **9 Frontend Native Unit Tests**: **100% Passed** (client parsing, stage mappings, validation guards).
- **Database Isolation Verified**: 0 synthetic test records added to `orderflow_sentinel.db`. Active orders remain exactly 513.

---

## 5. Important Source Files At a Glance

| Subsystem | Key Files | Functionality |
|---|---|---|
| **Entry Point** | [`backend/app/main.py`](file:///d:/Virtusa Jatayu/backend/app/main.py) | FastAPI app, CORS, lifespan database init, `/ui` SPA mount. |
| **Data Models** | [`backend/app/models/order.py`](file:///d:/Virtusa Jatayu/backend/app/models/order.py) | 7 SQLAlchemy models (`Order`, `OrderEvent`, `Incident`, `RCAReport`, `ResolutionAction`, `OperatorApproval`, `AuditLog`). |
| **Failure Detection** | [`backend/app/services/detector.py`](file:///d:/Virtusa Jatayu/backend/app/services/detector.py) | Flags 503, 422, and SLA breaches; creates incidents; invokes RCA. |
| **Policy Engine** | [`backend/app/policies/policy_engine.py`](file:///d:/Virtusa Jatayu/backend/app/policies/policy_engine.py) | Authoritative decision matrix; blocks illegal auto-actions. |
| **Self-Healing** | [`backend/app/services/resolution_service.py`](file:///d:/Virtusa Jatayu/backend/app/services/resolution_service.py) | Exponential backoff retry, idempotency keys, downstream verification. |
| **Human Approvals** | [`backend/app/services/approval_service.py`](file:///d:/Virtusa Jatayu/backend/app/services/approval_service.py) | Parameter validation, inventory re-allocation, journey resumption. |
| **AI Integration** | [`backend/app/ai/gemini_rca.py`](file:///d:/Virtusa Jatayu/backend/app/ai/gemini_rca.py) | Google Gemini client (`gemini-flash-latest`) + 5ms deterministic fallback. |
| **Frontend UI** | [`frontend/src/components/views/ViewD_LiveDemo.tsx`](file:///d:/Virtusa Jatayu/frontend/src/components/views/ViewD_LiveDemo.tsx) | Live Order Cockpit, 7-stage visual stepper, live telemetry, session reset. |

---

## 6. Required API Keys & Secrets

- **`GEMINI_API_KEY`**: Optional Google Gemini API Key configured in `.env`.
- If the key is omitted, invalid, or quota-limited, Sentinel **automatically activates its internal deterministic fallback engine**. The platform never crashes and preserves 100% functionality without internet access.

---

## 7. Known Architectural Limitations

1. **Single-Node SQLite Storage**: Designed as an in-process modular monolith with SQLite WAL mode. Scaling across a distributed Kubernetes cluster would require migrating the SQLAlchemy connection string to PostgreSQL.
2. **Synchronous REST Simulation**: Downstream microservices are simulated via internal FastAPI service classes rather than over an external network wire or message queue (Kafka/RabbitMQ).
3. **Advisory AI Boundary**: AI is intentionally not permitted to execute database mutations directly; all actions must route through the deterministic policy engine.
