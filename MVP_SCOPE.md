# MVP Scope Specification Document
## OrderFlow Sentinel — AI-Powered Self-Healing Order Failure Detection and Resolution Platform

---

### Document Control
- **Document Version:** 1.2.1 (Scope Freeze Baseline with Lifecycle, Approval & Type Harmonization)
- **Status:** Approved for Implementation Planning
- **Architecture Model:** Modular Monolith with Simulated Downstream Services and Optional Gemini Integration
- **Context:** Virtusa Jatayu Forward Deployed Engineer Hackathon

---

## 1. Product Objective & Core Boundary

The primary objective of the OrderFlow Sentinel MVP is to construct a fully functioning prototype that monitors a simulated multi-hop e-commerce order journey, detects failures deterministically, diagnoses root causes using telemetry evidence, enforces deterministic safety policies, executes safe self-healing actions, and verifies that recovery succeeded before resuming order progression.

The prototype demonstrates **genuine backend processing**. It does not perform cosmetic UI state flips.

---

## 2. Core Order Journey (7 Stages) & Order Lifecycle Semantics

The monitored transaction sequence traverses seven sequential stages across simulated downstream services:

$$\text{Customer Order} \longrightarrow \text{Address Validation} \longrightarrow \text{Payment} \longrightarrow \text{Inventory Reservation} \longrightarrow \text{Warehouse Fulfilment} \longrightarrow \text{Logistics} \longrightarrow \text{Customer Notification}$$

### 2.1 Order Lifecycle & Post-Recovery Progression Semantics
To eliminate lifecycle contradictions, the following state rules are strictly enforced:
1. **Order Remains `PROCESSING` During Recoverable Incidents:** Recoverable HTTP 503 errors and HTTP 422 inventory rejections do not make the order terminally `FAILED`. The order remains in `PROCESSING` while the affected stage is blocked pending investigation and resolution.
2. **Failure Tracked via Incident Lifecycle:** The disruption, investigation, and recovery are tracked independently through the linked `incident` record (`DETECTED` $\longrightarrow$ `ANALYZING` $\longrightarrow$ `RESOLVING` or `PENDING_APPROVAL` $\longrightarrow$ `RESOLVED`).
3. **Resumption After Downstream Verification:** When self-healing or human approval succeeds and downstream state verification passes:
   - The associated incident transitions to `RESOLVED`.
   - The order continues its journey in `PROCESSING`.
   - The remaining order stages continue (`FULFILMENT` $\longrightarrow$ `DELIVERY` $\longrightarrow$ `NOTIFICATION`).
   - The order transitions to `COMPLETED` **only after all seven stages succeed**.
4. **Strict Reservation of `FAILED`:** The `FAILED` status is reserved strictly for genuinely unrecoverable orders (e.g., operator rejects the recovery, or retries are exhausted without resolution). There is no transition from `FAILED` back to `PROCESSING`.

Each stage emits a structured telemetry event containing:
- `event_id`: Unique string identifier.
- `order_id`: Associated order reference.
- `correlation_id`: Distributed trace correlation UUID.
- `stage`: Current journey stage name.
- `service_name`: Executing service component.
- `endpoint`: Simulated HTTP route.
- `http_method`: HTTP verb (`GET`, `POST`, `PUT`).
- `http_status`: HTTP response status code (e.g., 200, 503, 422).
- `duration_ms`: Execution latency in milliseconds.
- `event_status`: `SUCCESS`, `FAILED`, or `DELAYED`.
- `payload_summary`: Sanitized request/response summary.
- `error_code` & `error_message`: Structured error details when applicable.
- `timestamp`: UTC timestamp.

*Downstream services are simulated within the backend application. No real payment gateways, customer PII, or external cloud services are accessed.*

---

## 3. The Three MVP Scenarios

The MVP detection and resolution engine is strictly scoped to three deterministic failure scenarios:

### Scenario 1 — HTTP 503 Self-Healing (Transient Technical Failure)
1. Ingest synthetic order (`status: PROCESSING`).
2. Advance journey through Address Validation and Payment.
3. Simulate an HTTP 503 Service Unavailable response at Inventory Reservation.
4. Persist telemetry event and detect API failure deterministically.
5. Generate an `incident` record (`API_ERROR`, `HTTP_503`, `status: DETECTED`). Order remains `PROCESSING` (stage blocked).
6. Produce an evidence-based advisory RCA report via Gemini API (or deterministic fallback).
7. Recommend `RETRY_WITH_BACKOFF` with `LOW` risk.
8. Policy engine checks the attempt count (`retry_count < 3`) and authorizes retry.
9. Execute idempotent retry with exponential backoff delay and unique `idempotency_key` (`attempt_number: 1`).
10. Downstream inventory service processes retry and returns HTTP 200.
11. State verification probe confirms inventory is reserved.
12. **Lifecycle Continuation:** Incident transitions to `RESOLVED`. Order continues in `PROCESSING` and advances through Fulfilment, Delivery, and Notification.
13. Order transitions to `COMPLETED` once all 7 stages succeed. Record in `audit_logs`.

### Scenario 2 — SLA Delay (Operational Bottleneck)
1. Ingest synthetic order and advance to Fulfilment.
2. Simulate a delayed fulfilment stage ($10,000\text{ms}$ execution time).
3. Compare elapsed duration against illustrative demo SLA threshold ($5,000\text{ms}$).
4. Detect SLA breach deterministically and create an `incident` (`ORDER_DELAY`, `SLA_BREACH`).
5. Flag order status as `DELAYED`.
6. Issue an operator alert displaying affected stage, elapsed duration, and SLA threshold.
7. Policy engine strictly prohibits automatic order cancellation or reassignment.
8. Order remains `DELAYED` awaiting operator investigation or downstream completion. Record in `audit_logs`.

### Scenario 3 — Hard Business Rejection & Human-in-the-Loop (Policy Constraint)
1. Ingest synthetic order and advance to Inventory Reservation.
2. Simulate an Out-of-Stock business rejection (HTTP 422 / Business Rule Violation).
3. Detect and classify failure deterministically as an unfixable `ORDER_REJECTION`. Order remains `PROCESSING` (blocked at Inventory).
4. Generate evidence-based RCA report identifying stock exhaustion.
5. Deterministic policy engine prohibits blind retries.
6. Create an `operator_approvals` record with `decision: PENDING` and `HIGH` risk.
7. Operator inspects incident, evidence, and suggested remedy.
8. Operator submits decision (`APPROVED` or `REJECTED`) with `selected_action` and `action_parameters` (e.g., `{"substitute_sku": "SKU-CYBER-500-ALT", "alternate_hub": "HUB-EAST-02"}`).
9. **Execution & State Branching:**
   - **If `APPROVED`:** Simulated adapter validates parameters, executes substitution, and verifies state. Incident transitions to `RESOLVED`. Order continues in `PROCESSING`, completes Fulfilment, Delivery, and Notification, and transitions to `COMPLETED`.
   - **If `REJECTED`:** Incident transitions to `REJECTED`. No retry executed. Order transitions to `FAILED`.
10. Persist operator decision, notes, and execution results in `audit_logs`.

*(A baseline healthy order `SCENARIO_0_CLEAN_RUN` is supported to confirm baseline pipeline health.)*

---

## 4. Architectural Boundaries, Retry & Idempotency Rules

1. **Architecture Style:** Modular Monolith with Simulated Downstream Services and Optional Gemini Integration.
2. **Zero Distributed Infrastructure:** No Redis, Kafka, RabbitMQ, Celery, or external container orchestrators.
3. **Database Layer:** SQLite with SQLAlchemy 2.0 ORM. SQLAlchemy reduces database migration effort, but database-specific behavior and queries may require adjustments if migrating to PostgreSQL.
4. **Retry Semantics:**
   - Maximum retry attempts: `max_retries = 3` after the initial failed request.
   - Initial failed request: `retry_count = 0`.
   - First retry: `retry_count = 1` (`attempt_number = 1`).
   - Second retry: `retry_count = 2` (`attempt_number = 2`).
   - Third retry: `retry_count = 3` (`attempt_number = 3`).
   - Further retries are prohibited.
   - If verification fails after 3 retries, incident transitions to `ESCALATED`.
   - `attempt_number` in `resolution_actions` strictly denotes the retry execution number (1, 2, or 3), not total HTTP requests.
5. **Idempotency Guarantees & Response Behavior:**
   - **Primary Authority:** Database `UNIQUE` constraints on `resolution_actions.idempotency_key` combined with transaction-safe checks. In-memory locks provide secondary single-process concurrency control.
   - **Repeated Request (Same Key & Same Action):** Returns the existing action record and execution result (HTTP 200) without re-executing downstream.
   - **Conflicting Request (Same Key & Different Action / Payload):** Rejects the operation and returns HTTP 409 Conflict.
6. **Human Approval Scope:** The MVP workflow strictly supports `APPROVED` and `REJECTED` operator decisions. Override workflows are excluded from the MVP.
7. **AI Advisory Role (Zero Privileged Execution):**
   - Gemini produces advisory diagnoses only; it cannot execute state mutations.
   - RCA output provides `evidence_strength` (`HIGH`, `MEDIUM`, `LOW`) and `corroborating_signals_count`. LLM confidence scores are never treated as calibrated probabilities.
   - Internal chain-of-thought is excluded; output provides a concise, evidence-grounded explanation.
   - Model name is configured via `GEMINI_MODEL_ID` (verified during runtime, no permanent hardcoded fallback). API key is never exposed.
   - If `GEMINI_API_KEY` is absent or the API fails, an internal deterministic rule engine generates identical structured diagnoses.
   - Gemini availability is an optional health check dependency; missing credentials do not block system startup.
8. **Illustrative Demo SLA Baselines:** Stage SLA thresholds are explicitly configured as illustrative demo values for hackathon evaluation and do not represent production SLAs.
9. **Audit Logging Terminology:** Application-level append-only audit logging. Audit records cannot be modified or deleted through the application's exposed API.
10. **Near-Real-Time UI Monitoring:** The UI utilizes 3-second polling for near-real-time updates of order and incident state.

---

## 5. Frontend Structure & Early Integration

The interface is structured into **three cohesive views** with persistent simulation controls, brought forward early in the implementation sequence:
- **Milestone 1:** Minimal frontend view to trigger and observe Scenario 1.
- **Milestone 2:** Extend frontend with SLA delay incident badges and timing comparisons.
- **Milestone 3:** Extend frontend with Human Approval Queue and operator decision actions (`APPROVE`, `REJECT`).
- **Milestone 4:** Full dashboard polish across the three cohesive views:
  1. *Dashboard & Monitoring View*
  2. *Order Journey & Incident RCA View*
  3. *Human Approval Queue & Audit Trail View*
  4. *Persistent Simulation Control Header/Drawer*

---

## 6. Explicit Project Exclusions

The following elements are strictly excluded from the MVP:
- Real payment gateway or merchant account integrations.
- Production customer PII or external databases.
- Custom LLM fine-tuning or training.
- Supervised ML training on synthetic datasets (e.g., Random Forest or Isolation Forest).
- Redis caching, distributed message queues, or Celery task workers.
- Complex multi-role RBAC systems and operator override workflows.
- Eight disjointed frontend pages.
- Unverifiable production claims regarding enterprise recovery percentages.

---
*End of MVP_SCOPE.md*
