# Product Requirements Document (PRD)
## OrderFlow Sentinel — AI-Powered Self-Healing Order Failure Detection and Resolution Platform

---

### Document Control
- **Document Version:** 1.2.1 (Scope Freeze Baseline with Lifecycle, Approval & Type Harmonization)
- **Status:** Approved for Implementation Planning
- **Author:** Lead Solutions Architect & Forward Deployed Engineer
- **Target Audience:** Virtusa Jatayu Selection Committee, Evaluators, Engineering Leads
- **Architecture Model:** Modular Monolith with Simulated Downstream Services and Optional Gemini Integration

---

## 1. Executive Summary & Vision

### 1.1 Executive Summary
Modern enterprise commerce orders traverse a distributed pipeline of independently functioning services: Customer Order Ingestion, Address Validation, Payment Processing, Inventory Reservation, Warehouse Fulfilment, Logistics, and Customer Notification. A disruption at any intermediate hop—such as a transient 503, an unhandled queue delay, or an out-of-stock rejection—stalls the journey, resulting in degraded user experience and operational overhead.

**OrderFlow Sentinel** is an operations and self-healing prototype engineered for the Virtusa Jatayu Hackathon. Built as a **Modular Monolith with Simulated Downstream Services and Optional Gemini Integration**, it provides near-real-time monitoring of order telemetry via 3-second polling, detects failures deterministically across three target scenarios, diagnoses root causes using ingested telemetry evidence (via Gemini API or deterministic fallback), selects safe recovery actions via policy-as-code, and asserts state verification before resuming order progression. High-risk operations and business rejections are routed to an operator Human-in-the-Loop (HITL) approval queue.

### 1.2 Core Operating Principles
1. **Safe Automation with Human Control:** Low-risk, idempotent technical actions (e.g., exponential backoff retries on transient 503 errors) are automated within policy bounds. High-risk actions and business-policy exceptions (e.g., out-of-stock substitutions) strictly require human operator review.
2. **Standardized Order Lifecycle & Non-Terminal Recovery:**
   - Recoverable HTTP 503 errors and HTTP 422 inventory rejections do not make the order terminally `FAILED`.
   - The order remains in `PROCESSING` while the affected stage is blocked pending investigation and resolution.
   - Disruptions and recovery workflows are tracked independently through the linked `incident` record.
   - When recovery succeeds and downstream state verification passes, the incident transitions to `RESOLVED`, the order continues in `PROCESSING`, executes remaining stages (`FULFILMENT` $\longrightarrow$ `DELIVERY` $\longrightarrow$ `NOTIFICATION`), and transitions to `COMPLETED` **only after all seven stages succeed**.
   - The status `FAILED` is reserved strictly for genuinely unrecoverable orders (e.g., operator rejection or exhausted retries). There is no transition from `FAILED` back to `PROCESSING`.
3. **Evidence-Grounded AI (Advisory Only):** The Gemini Root Cause Analysis (RCA) engine operates as an advisory layer. It synthesizes ingested telemetry logs and HTTP responses into structured diagnoses. It cannot invent non-existent evidence or directly execute state mutations.
4. **Deterministic Safety Guardrails & Policy Authority:** A deterministic policy engine authorizes every action against configured retry caps (`max_retries = 3` after initial failure) and risk thresholds. If Gemini is unavailable, an internal deterministic rule engine generates identical structured diagnoses.
5. **Verified Recovery Precondition:** An order stage is never treated as recovered simply because a recovery action or retry was dispatched. Recovery requires explicit state verification against the downstream service.
6. **Primary Database Idempotency:** Database `UNIQUE` constraints on `idempotency_key` and transaction-safe checks serve as the primary idempotency safeguards. Repeated requests with the same key and action return the existing result (HTTP 200); conflicting actions with the same key return HTTP 409 Conflict.
7. **Application-Level Append-Only Audit Logging:** Audit records cannot be modified or deleted through the application's exposed API.

---

## 2. Problem Statement & Prototype Evaluation Goals

### 2.1 Problem Statement
When an order journey fails in a multi-hop pipeline, operations teams typically discover the failure through delayed dashboards or customer tickets. Investigating fragmented service logs increases Mean Time to Detect (MTTD) and Mean Time to Resolve (MTTR).

### 2.2 Prototype Verification Metrics
Unlike production benchmarks, this hackathon MVP is evaluated against verifiable prototype execution criteria:
- **Detection Latency:** Deterministic detection within $< 500\text{ms}$ of telemetry ingestion.
- **Explainability:** 100% of detected incidents produce an evidence-grounded RCA report citing specific error codes and timestamps.
- **Idempotency Guarantee:** Repeated recovery requests with the same key return cached results without double execution; conflicting payloads return HTTP 409.
- **Verification Guarantee:** 100% of resolved incidents undergo downstream state assertion before order processing resumes.
- **Zero-Crash Resilience:** System remains fully operational even if `GEMINI_API_KEY` is omitted or network calls fail.

---

## 3. Failure Taxonomy & Scope Freeze

The prototype categorizes operational incidents into three failure categories, demonstrating deterministic detection and resolution across three core scenarios:

```
                                  Order Failure Categories
                                             │
         ┌───────────────────────────────────┼──────────────────────────────────┐
         │                                   │                                  │
         ▼                                   ▼                                  ▼
1. API Response Errors              2. Order Journey Delays            3. Order Rejections
(HTTP 503 Transient)                (Fulfilment SLA Breach)            (Inventory Out-of-Stock)
         │                                   │                                  │
   [Scenario 1]                        [Scenario 2]                       [Scenario 3]
Auto-retry with backoff             Detect delay anomaly,              Prohibit blind retry,
and state verification;             alert operator without             route to human approval,
order continues PROCESSING.         auto-cancellation.                 validate params & resume.
```

> [!IMPORTANT]
> The MVP provides fully implemented detection and resolution workflows specifically for the three targeted scenarios (HTTP 503 transient error, Fulfilment SLA delay, and HTTP 422 out-of-stock rejection). It does not claim full recovery implementations for arbitrary 4xx/5xx errors.

### 3.1 Failure Modes in MVP Scope
1. **API Response Error (Scenario 1 — HTTP 503 Self-Healing):**
   - *Condition:* Downstream Inventory Service returns HTTP 503 Service Unavailable due to transient backpressure.
   - *Action:* Order remains `PROCESSING` (stage blocked). Incident created (`status: DETECTED`). Recommend `RETRY_WITH_BACKOFF` with `LOW` risk. Policy authorizes retry if `retry_count < 3`. Dispatches retry with idempotency key (`attempt_number: 1`), verifies HTTP 200 and stock reservation, marks incident `RESOLVED`, order continues `PROCESSING` across Fulfilment, Delivery, and Notification, and marks order `COMPLETED`.
2. **Order Delay (Scenario 2 — SLA Delay Detection & Alerting):**
   - *Condition:* Fulfilment stage exceeds its configured illustrative demo SLA threshold.
   - *Action:* Detect delay, create `ORDER_DELAY` incident, update order status to `DELAYED`, and issue an operator alert. The policy engine strictly prohibits automatic cancellation or reassignment.
3. **Order Rejection (Scenario 3 — Hard Business Rejection & HITL):**
   - *Condition:* Inventory Service returns Out-of-Stock rejection (HTTP 422).
   - *Action:* Classify as a permanent business rejection. Order remains `PROCESSING` (stage blocked). Prohibit automatic retry. Create a pending human approval request with `HIGH` risk. Operator reviews evidence and submits decision (`APPROVED` or `REJECTED`) with `selected_action` and `action_parameters` (substitute SKU and alternate hub). If approved, the simulated adapter validates parameters, executes substitution, and verifies state; incident transitions to `RESOLVED`, order continues in `PROCESSING`, finishes remaining stages, and reaches `COMPLETED`. If rejected, incident transitions to `REJECTED` and order transitions to `FAILED`.

*(A baseline healthy order `SCENARIO_0_CLEAN_RUN` is supported to confirm baseline pipeline health.)*

---

## 4. End-to-End Order Journey Definition

Orders progress sequentially across seven journey stages:

$$\text{Customer Order} \longrightarrow \text{Address Validation} \longrightarrow \text{Payment} \longrightarrow \text{Inventory Reservation} \longrightarrow \text{Warehouse Fulfilment} \longrightarrow \text{Logistics} \longrightarrow \text{Customer Notification}$$

### Stage Definitions & Service Responsibilities:
1. **Customer Order (`order_service`):** Ingestion of customer reference, product SKU, and amount. Generates global `order_id` and `correlation_id`.
2. **Address Validation (`address_service`):** Verification of shipping destination.
3. **Payment Processing (`payment_service`):** Transaction capture.
4. **Inventory Reservation (`inventory_service`):** Stock allocation.
5. **Warehouse Fulfilment (`fulfilment_service`):** Pick, pack, and package routing.
6. **Logistics (`logistics_service`):** Dispatch manifest and carrier tracking generation.
7. **Customer Notification (`notification_service`):** Dispatch of customer confirmation message.

---

## 5. Standardized Lifecycle States

### 5.1 Order Status (`order_status`)
- `PENDING`: Order record initialized.
- `PROCESSING`: Journey in progress across stages (active during normal processing, during recoverable incident investigation, and during post-healing progression).
- `COMPLETED`: All 7 stages finished successfully (terminal healthy state).
- `FAILED`: Genuinely unrecoverable error (terminal failure state; e.g. operator rejection or exhausted retries). No transition back to `PROCESSING`.
- `DELAYED`: Order stage exceeded configured SLA threshold (awaiting investigation or completion).
- `CANCELLED`: Order cancelled by operator or customer.

### 5.2 Incident Status (`incident_status`)
- `DETECTED`: Failure flagged by detection engine.
- `ANALYZING`: RCA report generation underway.
- `PENDING_APPROVAL`: High-risk or business rejection awaiting human operator decision.
- `RESOLVING`: Recovery action authorized and executing.
- `RESOLVED`: Downstream state assertion verified recovery.
- `ESCALATED`: Retries exhausted (3 failed retry attempts) or unrecoverable condition escalated.
- `REJECTED`: Recovery rejected by operator.

### 5.3 Resolution Action Execution Status (`execution_status`)
- `PENDING`: Action queued.
- `EXECUTING`: Dispatched to service adapter.
- `VERIFYING`: Action completed; downstream state verification in progress.
- `SUCCEEDED`: Verification passed; recovery confirmed.
- `FAILED`: Execution or verification failed.

### 5.4 Operator Approval Decision (`decision`)
- `PENDING`: Awaiting human review.
- `APPROVED`: Operator authorized selected action with validated parameters.
- `REJECTED`: Operator rejected recovery action.

---

## 6. Functional Requirements

### 6.1 Module A: Order Management
- **FR-A1:** Store and manage orders with attributes: `order_id`, `correlation_id`, `customer_id`, `customer_name`, `customer_email`, `product_sku`, `product_name`, `order_amount`, `currency`, `current_stage`, `order_status`, `payment_status`, `inventory_status`, `fulfilment_status`, `created_at`, `updated_at`.
- **FR-A2:** Support generation of synthetic demonstration orders.
- **FR-A3:** Support order retrieval and multi-parameter filtering.

### 6.2 Module B: Journey Monitoring & Telemetry
- **FR-B1:** Ingest and persist telemetry events containing: `event_id`, `order_id`, `correlation_id`, `stage`, `service_name`, `endpoint`, `http_method`, `http_status`, `duration_ms`, `event_status`, `payload_summary`, `error_code`, `error_message`, `timestamp`.
- **FR-B2:** Correlate events by `order_id` into an ordered 7-stage chronological timeline.

### 6.3 Module C: Failure Detection Engine
- **FR-C1:** Real-time deterministic detection of target HTTP status anomalies (HTTP 503, HTTP 422).
- **FR-C2:** Compare stage duration against illustrative demo SLA thresholds configured in `system_policies`.
- **FR-C3:** Automatically create an `incident` record linked to `order_id`.

### 6.4 Module D: AI Root Cause Analysis (RCA) Agent
- **FR-D1:** Synthesizes incident telemetry into an advisory diagnostic report via Gemini API.
- **FR-D2:** Enforces structured JSON output schema:
  - `failure_category`: (`API_ERROR` | `ORDER_DELAY` | `ORDER_REJECTION`)
  - `affected_service`: string
  - `observed_evidence`: array of factual telemetry strings
  - `probable_root_cause`: concise narrative explanation
  - `evidence_strength`: (`HIGH` | `MEDIUM` | `LOW`) based on telemetry completeness
  - `corroborating_signals_count`: integer count of supporting signals
  - `recommended_action`: string code
  - `risk_level`: (`LOW` | `MEDIUM` | `HIGH` | `CRITICAL`)
  - `explanation`: concise evidence-grounded explanation
  - `model_source`: configured model ID or `DETERMINISTIC_FALLBACK`
- **FR-D3:** Model configuration via `GEMINI_MODEL_ID` and `GEMINI_API_KEY`. The active model ID is verified at runtime; never expose the API key.
- **FR-D4:** Do not request or store internal LLM chain-of-thought.
- **FR-D5:** Do not present LLM outputs as calibrated mathematical probabilities.
- **FR-D6:** Deterministic Fallback: When credentials are missing or the API call fails, internal deterministic rules generate an identical structured report.

### 6.5 Module E: Policy-as-Code, Retry Policy & Idempotency
- **FR-E1:** Authorize candidate actions strictly through the deterministic policy engine.
- **FR-E2 (Standardized Retry Semantics):**
  - Maximum retry attempts: `max_retries = 3` after the initial failed request.
  - Initial failed request has `retry_count = 0`.
  - First retry has `retry_count = 1` (`attempt_number = 1`).
  - Second retry has `retry_count = 2` (`attempt_number = 2`).
  - Third retry has `retry_count = 3` (`attempt_number = 3`).
  - Further retries are strictly prohibited.
  - After 3 unsuccessful retries, incident transitions to `ESCALATED`.
  - `attempt_number` in resolution actions strictly denotes retry execution numbers (1, 2, 3), not total requests.
- **FR-E3 (Idempotency Response Behavior):**
  - Primary Authority: Database `UNIQUE` constraint on `idempotency_key` (`idemp_{order_id}_{stage}_{attempt}`).
  - Repeated request with identical key and action returns cached record (HTTP 200).
  - Conflicting request with identical key and different action returns HTTP 409 Conflict.
- **FR-E4:** High-risk actions (`HIGH` or `CRITICAL` risk, e.g., out-of-stock rejections) must route to the Human Approval Queue.

### 6.6 Module F: Human-in-the-Loop (HITL) Approval Queue
- **FR-F1:** Present pending approvals with incident details, RCA diagnosis, telemetry evidence, risk level, and suggested action.
- **FR-F2:** Operator can choose `APPROVE` or `REJECT` (Override is excluded from MVP).
- **FR-F3 (Structured Approval Contract):** Operator approval requires `decision`, `operator_id`, `operator_name`, `operator_notes`, `selected_action`, and `action_parameters` (identifying substitute SKU and alternate warehouse hub).
- **FR-F4:** The simulated inventory adapter validates `selected_action` and `action_parameters` before execution. Upon verified success, incident transitions to `RESOLVED` and order continues in `PROCESSING`. If rejected, incident transitions to `REJECTED` and order transitions to `FAILED`.
- **FR-F5:** Record operator identity, decision, notes, parameters, and timestamp in `audit_logs`.

### 6.7 Module G: Self-Healing Verification
- **FR-G1:** Following action execution, dispatch a verification probe asserting HTTP 200 response and downstream state progression.
- **FR-G2:** Transition incident to `RESOLVED` and order continues in `PROCESSING` through remaining stages.

### 6.8 Module H: Consolidated Frontend User Interface
Consolidate the interface into **three cohesive views** with persistent simulation controls, updated via near-real-time 3-second polling:
1. **Dashboard & Monitoring View:** Summary KPIs, failure distribution, and order monitoring data grid.
2. **Order Journey & Incident RCA View:** Chronological 7-stage interactive timeline, telemetry event inspector, and Gemini/Fallback RCA evidence card.
3. **Human Approval Queue & Audit Trail View:** Pending operator review queue with Approve/Reject controls, and queryable append-only audit trail table.
4. **Persistent Simulation Control Header/Drawer:** Instant one-click triggers for Scenarios 1, 2, and 3.

---

## 7. Illustrative Demo SLA Thresholds

> [!NOTE]
> The following SLA thresholds are configurable illustrative demo values established specifically for hackathon evaluation and demonstration. They do not represent actual industry or production SLAs.

| Stage Name | Illustrative Demo SLA | Demo Injected Value | Observed Behavior |
| :--- | :--- | :--- | :--- |
| `CUSTOMER_ORDER` | $1,000\text{ms}$ | $50\text{ms}$ | Normal execution |
| `ADDRESS_VALIDATION` | $2,000\text{ms}$ | $120\text{ms}$ | Normal execution |
| `PAYMENT` | $3,000\text{ms}$ | $450\text{ms}$ | Normal execution |
| `INVENTORY` | $2,000\text{ms}$ | $300\text{ms}$ | Normal execution |
| `FULFILMENT` | $5,000\text{ms}$ | $10,000\text{ms}$ | **SLA Breach Detected (Scenario 2)** |
| `DELIVERY` | $5,000\text{ms}$ | $200\text{ms}$ | Normal execution |
| `NOTIFICATION` | $1,000\text{ms}$ | $80\text{ms}$ | Normal execution |

---

## 8. Non-Functional & Security Requirements

1. **System Health & Optional Gemini Dependency:**
   - The `/health` endpoint reports system readiness based on SQLite connectivity and schema integrity.
   - Gemini API availability is an **optional dependency**; if unavailable, the application remains fully healthy and operational via deterministic fallback.
2. **Security & Secrets Isolation:**
   - Secrets (`GEMINI_API_KEY`) are managed via environment variables and `.env`.
   - Never expose API keys to frontend clients or API responses.
3. **Data Portability:**
   - SQLAlchemy reduces database migration effort, but database-specific behavior and queries may require adjustments if migrating to PostgreSQL.

---
*End of PRD.md*
