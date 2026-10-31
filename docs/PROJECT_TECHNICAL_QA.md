# OrderFlow Sentinel — Technical Interview & Evaluation Q&A (42 Questions)

> **Purpose**: A comprehensive guide for technical interviews, hackathon jury evaluations, and code walk-throughs covering every architectural decision in OrderFlow Sentinel.

---

## Category 1: Architecture & System Design

#### Q1: What is OrderFlow Sentinel in one elevator pitch?
**Answer**: OrderFlow Sentinel is an AI-powered, policy-governed self-healing order processing platform. It monitors multi-hop e-commerce order journeys across 7 distinct stages, detects transient and permanent microservice failures in real time, generates advisory root cause analyses using Google Gemini, and executes verified, idempotent self-healing actions governed by a deterministic policy engine.

#### Q2: Why is self-healing necessary in modern e-commerce distributed systems?
**Answer**: In microservice architectures, an order must traverse multiple independent downstream services (inventory, payment gateways, fraud detectors, 3PL fulfilment). A transient network glitch (HTTP 503) or brief latency spike would normally drop the order, losing revenue and creating customer frustration. Self-healing allows the system to autonomously recover from transient faults while safely escalating non-recoverable business rejections to human operators.

#### Q3: What is the core architectural safeguard regarding AI in this platform?
**Answer**: The fundamental principle is **"AI Advisory, Deterministic Authority"**. Google Gemini acts purely in an advisory capacity—it suggests probable causes and candidate actions, but has **zero execution authority**. Every mutation must be evaluated, approved, and executed by our deterministic `PolicyEngine`.

#### Q4: Why did you not use Kafka, Redis, or Celery in this implementation?
**Answer**: In strict adherence to Version 1.2.1 specifications, introducing heavyweight message brokers or cache daemons would create unnecessary operational complexity and external infrastructure failure points for this single-node vertical slice. SQLite in WAL mode combined with FastAPI's native asynchronous concurrency and background tasks provides high throughput, zero external dependencies, and complete portability.

#### Q5: How are the 7 stages of an order sequenced?
**Answer**: The stages execute sequentially: `VALIDATION` $\to$ `INVENTORY` $\to$ `PAYMENT` $\to$ `FRAUD_CHECK` $\to$ `FULFILMENT` $\to$ `DELIVERY` $\to$ `NOTIFICATION`. If any stage encounters a failure or SLA delay, the pipeline halts progression at that specific stage until recovery or operator review occurs.

---

## Category 2: FastAPI, Backend & API Contracts

#### Q6: Why did you choose FastAPI over Flask or Django?
**Answer**: FastAPI provides native asynchronous request handling, automatic OpenAPI/Swagger documentation generation, dependency injection for database sessions, and high-performance schema serialization via Pydantic V2.

#### Q7: How does FastAPI manage database connection lifecycles in this project?
**Answer**: Through the `get_db()` dependency generator in `backend/app/db/session.py`. Each HTTP request receives a dedicated SQLAlchemy session that commits on success, rolls back on exception, and closes deterministically in a `finally` block.

#### Q8: What standard structure do all API responses follow?
**Answer**: All endpoints return a standardized generic wrapper `ApiResponse[T]` containing:
- `success: bool`
- `data: T`
- `message: str`
This guarantees predictable client-side consumption across all views.

#### Q9: How is server-side pagination implemented for orders?
**Answer**: The `/api/v1/orders` endpoint accepts `skip` and `limit` query parameters, querying the database via `.offset(skip).limit(limit).all()`. It also computes total record counts, enabling the frontend to navigate past the initial 50 records cleanly.

#### Q10: How does the FastAPI app serve the React frontend in production?
**Answer**: In `backend/app/main.py`, FastAPI checks for the compiled `frontend/dist/` bundle. If present, it mounts static asset routes and serves `index.html` on the `/ui` route, allowing single-process full-stack deployment.

---

## Category 3: React Frontend & State Management

#### Q11: What frontend stack is used?
**Answer**: React 18, Vite, TypeScript, and Tailwind CSS, supplemented by Lucide React for UI iconography and Recharts for data visualization.

#### Q12: How does the frontend communicate with the backend?
**Answer**: Through a strongly-typed API client in `frontend/src/api/client.ts`. In development, Vite's dev server proxies `/api` requests to `http://127.0.0.1:8000`, eliminating CORS issues.

#### Q13: How is deep-linking implemented between views?
**Answer**: When an operator clicks **Inspect Journey** in View A or View D, the application passes `orderId` to top-level state in `App.tsx` and automatically switches `activeTab` to View B, pre-loading telemetry events and RCA reports.

#### Q14: How does View D isolate live demonstration orders?
**Answer**: View D initializes a persistent `demoSessionId` (e.g., `demo-1730372400`) in local storage. All orders submitted from this cockpit include `is_demo_order: true` and `demo_session_id`. When querying orders, View D passes these query parameters to display only the active session's orders.

#### Q15: How are concurrent double-clicks prevented on scenario execution buttons?
**Answer**: Frontend buttons maintain an `isTriggering` loading state that immediately disables the button and applies visual spinner feedback until the API call finishes.

---

## Category 4: SQLAlchemy & Database Architecture

#### Q16: Why did you configure SQLite in WAL mode?
**Answer**: Standard SQLite uses rollback journals that lock the entire database file during writes, blocking readers and causing `database is locked` errors during concurrent background tasks. Write-Ahead Logging (WAL) allows concurrent readers and writers without blocking.

#### Q17: What are the 7 primary database tables in the schema?
**Answer**: `orders`, `order_events`, `incidents`, `rca_reports`, `resolution_actions`, `operator_approvals`, and `audit_logs`.

#### Q18: What is the relationship between `Order` and `OrderEvent`?
**Answer**: A one-to-many relationship (`Order.events`). Every stage hop, whether successful or failed, writes an immutable `OrderEvent` recording HTTP status, endpoint, latency, and response summary.

#### Q19: How are database migrations handled without Alembic?
**Answer**: In `backend/app/db/session.py`, `init_db()` invokes `Base.metadata.create_all()` and inspects table pragma columns. If new columns (such as `is_demo_order` or `demo_session_id`) are absent, it executes direct `ALTER TABLE` statements automatically.

#### Q20: Why must you never delete `orderflow_sentinel.db`?
**Answer**: The database holds **513 persistent historical orders** and **57 pending approval records** required for baseline analytics, SLA tracking, and audit compliance.

---

## Category 5: Failure Detection & Self-Healing Lifecycle

#### Q21: What triggers Scenario 1?
**Answer**: An injected HTTP 503 Service Unavailable error at Stage 3 (`PAYMENT`).

#### Q22: What constitutes the self-healing resolution in Scenario 1?
**Answer**: The detector identifies a transient failure, advisory RCA recommends `RETRY_WITH_BACKOFF`, the policy engine authorizes retry, the resolution service applies exponential backoff with a unique idempotency key, verifies downstream payment status (`CHARGE_CAPTURED`), and resumes the order journey to `COMPLETED`.

#### Q23: What is idempotency and how is it enforced?
**Answer**: Idempotency guarantees that executing the same operation multiple times produces the exact same outcome without duplicate side effects (e.g., charging a customer twice). We enforce this by generating unique cryptographic keys (`ResolutionAction.idempotency_key`) and checking for existing successful executions before invoking downstream APIs.

#### Q24: What happens if an automated retry fails repeatedly in Scenario 1?
**Answer**: The system increments `incident.retry_count`. Once `retry_count` reaches `max_retries` (3), the policy engine blocks further automated retries and escalates the incident status to `ESCALATED`.

#### Q25: Why is downstream verification mandatory before declaring recovery?
**Answer**: Simply receiving an HTTP 200 on retry is insufficient—downstream microservices may return 200 asynchronously while the underlying state is still corrupt. Sentinel executes a verification probe (`GET /payments/verify`) confirming `CHARGE_CAPTURED` before marking the incident `RESOLVED`.

---

## Category 6: SLA Monitoring & Operator Alerting

#### Q26: How does SLA monitoring work in Scenario 2?
**Answer**: During Stage 5 (`FULFILMENT`), the simulator injects 8500ms of simulated warehouse latency. The detector checks duration against the configured demo SLA threshold (`SLA_STAGE_FULFILMENT_MS` = 5000ms).

#### Q27: What happens to the order when an SLA breach occurs?
**Answer**: The order immediately transitions from `PROCESSING` to **`DELAYED`**. An `Incident` with `failure_type = "SLA_BREACH"` is created.

#### Q28: Why does Scenario 2 not automatically cancel the order or expedite it?
**Answer**: Under Version 1.2.1 compliance rules, automatic cancellation or unauthorized warehouse reassignment is strictly prohibited because warehouse pickers may have already physically pulled the inventory. The system issues an **Operator Alert** keeping the order safely `DELAYED` pending human investigation.

---

## Category 7: Human-in-the-Loop & Business Rejections

#### Q29: What triggers Scenario 3?
**Answer**: An injected HTTP 422 Unprocessable Entity (`Primary SKU Out of Stock`) at Stage 2 (`INVENTORY`).

#### Q30: Why is HTTP 422 treated differently than HTTP 503?
**Answer**: HTTP 503 is a transient infrastructure glitch that can resolve itself on retry. HTTP 422 is a **permanent business rejection**—the item is physically out of stock. Retrying with the same SKU will fail 100% of the time and waste system resources.

#### Q31: How does the Policy Engine handle HTTP 422?
**Answer**: It intercepts the failure and **strictly prohibits automated retry**. It creates an `OperatorApproval` record (`APP-XXXX`) with status `PENDING` and holds the order in `PROCESSING` (inventory stage blocked).

#### Q32: What parameters does the operator provide to approve Scenario 3?
**Answer**: The operator must provide a validated `substitute_sku` (e.g., `SKU-CYBER-500-ALT`) and an `alternate_hub` (e.g., `HUB-EAST-02`).

#### Q33: What happens if an operator submits a blank substitute SKU?
**Answer**: Both the frontend validation and backend `approval_service.py` reject the request with `400 Bad Request`, preventing incomplete or corrupt orders from resuming.

---

## Category 8: Google Gemini AI Integration & Fallback

#### Q34: What role does Google Gemini play in OrderFlow Sentinel?
**Answer**: Google Gemini acts as an **advisory intelligence engine**. It analyzes telemetry evidence and outputs structured JSON containing diagnosed root cause, evidence strength, recommended action, and risk level.

#### Q35: Which Gemini model is used?
**Answer**: `gemini-flash-latest` via the official `google-genai` Python SDK.

#### Q36: How does deterministic fallback work when Gemini is unavailable?
**Answer**: In `backend/app/ai/gemini_rca.py`, if the API key is missing or the external call fails (timeout, 404, 503, quota exhaustion), the system catches the exception and immediately invokes `_generate_deterministic_fallback()`. This evaluates predefined domain rules and returns the exact same structured diagnosis in under 5ms.

#### Q37: Can the entire application run without an internet connection or API key?
**Answer**: **Yes, 100%.** Deterministic fallback is completely autonomous, offline-capable, and preserves all scenario recovery behaviors.

---

## Category 9: Security, Auditability & Testing

#### Q38: How is auditability enforced?
**Answer**: Through the immutable `audit_logs` table. Every significant state transition (`ORDER_CREATED`, `INCIDENT_DETECTED`, `RCA_COMPLETED`, `APPROVAL_REQUESTED`, `APPROVAL_DECIDED`, `RESOLUTION_VERIFIED`) writes an append-only row recording `actor_type`, `actor_id`, and timestamp.

#### Q39: How do automated tests prevent polluting the real database?
**Answer**: In `backend/tests/conftest.py`, Pytest fixtures create an isolated temporary SQLite database for test execution. The persistent `orderflow_sentinel.db` remains 100% untouched.

#### Q40: What is the distribution in 🎲 Random Demo Mode?
**Answer**:
- 50% Clean Run (Scenario 0)
- 25% HTTP 503 Self-Healing (Scenario 1)
- 15% SLA Delay Alert (Scenario 2)
- 10% Hard Rejection & HITL Approval (Scenario 3)

#### Q41: How does "Reset Demo Session" protect historical data?
**Answer**: The reset API strictly filters on `Order.demo_session_id == session_id` AND `Order.is_demo_order == True`. Historical orders have `is_demo_order = False` and `demo_session_id = NULL`, making accidental deletion impossible.

#### Q42: What are the current architectural limitations and future roadmap items?
**Answer**: Current implementation is a single-node system running on SQLite. Future roadmap items (Milestone 5+) include distributed PostgreSQL clustering, multi-region Kafka event streaming, Redis distributed locks, and automated warehouse IoT webhook callbacks.

