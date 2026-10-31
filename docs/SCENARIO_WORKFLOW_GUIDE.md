# OrderFlow Sentinel — Scenario Workflow Guide

**Document Version:** 1.2.1  
**Target Audience:** Operations Engineers, QA Automation Testers, Evaluators  
**Execution Environment:** Windows PowerShell, Google Chrome  
**Canonical Endpoint:** `POST /api/v1/simulation/trigger-scenario`  

---

## 1. Overview of the Four Implemented Scenarios

OrderFlow Sentinel implements four complete, end-to-end scenarios covering nominal execution, transient self-healing, performance degradation alerting, and high-risk human approval gating:

| Scenario Key | Name | Primary Failure Mode | Resolution Mechanism | Final Status |
|---|---|---|---|---|
| `SCENARIO_0_CLEAN_RUN` | Clean Baseline Run | None (Nominal) | Sequential 7-stage advancement | `COMPLETED` |
| `SCENARIO_1_HTTP_503_SELF_HEAL` | HTTP 503 Self-Healing | Downstream 503 Outage at Inventory | Advisory RCA $\rightarrow$ Policy-authorized idempotent retry with backoff $\rightarrow$ Downstream verification | `COMPLETED` |
| `SCENARIO_2_SLA_DELAY` | SLA Latency Breach | 10,000ms Latency at Fulfilment | SLA evaluator detects breach $\rightarrow$ Transitions to `DELAYED` $\rightarrow$ Operator alert issued | `DELAYED` |
| `SCENARIO_3_HARD_REJECTION` | Business Rejection (422) | Out-of-Stock (HTTP 422) at Inventory | Policy blocks auto-retry $\rightarrow$ Queued in Human Approval Queue $\rightarrow$ Operator substitution | `COMPLETED` or `FAILED` |

---

## 2. Scenario 0: Clean Baseline Run (`SCENARIO_0_CLEAN_RUN`)

### 2.1 Technical Workflow
1. **Trigger:** Dispatched via UI button or API request to `POST /api/v1/simulation/trigger-scenario` with `{"scenario_key": "SCENARIO_0_CLEAN_RUN"}`.
2. **Order Creation:** `order_service.create_order()` initializes the order entity with `order_status: "PROCESSING"`.
3. **Execution across 7 Stages:** The simulator executes each stage sequentially:
   - `CUSTOMER_ORDER` (45ms, HTTP 200)
   - `ADDRESS_VALIDATION` (112ms, HTTP 200)
   - `PAYMENT` (420ms, HTTP 200)
   - `INVENTORY` (180ms, HTTP 200)
   - `FULFILMENT` (310ms, HTTP 200)
   - `DELIVERY` (250ms, HTTP 200)
   - `NOTIFICATION` (90ms, HTTP 200)
4. **Completion:** Upon successful completion of Stage 7, `order_service` updates `order_status = "COMPLETED"`.

### 2.2 Expected Behaviors & State Changes
- **UI Behavior:** View A shows a newly ingested order with a green `COMPLETED` badge. Clicking "Inspect Journey" shows 7 green checkmarks in View B.
- **Database Changes:** 
  - 1 row inserted into `orders` (`order_status = "COMPLETED"`).
  - 7 rows inserted into `order_events` (all with `http_status = 200`, `event_status = "SUCCESS"`).
  - 0 rows inserted into `incidents` and `operator_approvals`.
- **Audit Events:** `ORDER_INGESTED` and `ORDER_COMPLETED`.
- **Common Failure Conditions:** None (baseline scenario).

---

## 3. Scenario 1: HTTP 503 Inventory Self-Healing (`SCENARIO_1_HTTP_503_SELF_HEAL`)

### 3.1 Technical Workflow
1. **Trigger:** Dispatched with `scenario_key: "SCENARIO_1_HTTP_503_SELF_HEAL"`.
2. **Fault Injection:** In `simulator.py`, a simulated transient database connection pool exhaustion fault is injected for the inventory service on Stage 4 (`POST /v1/inventory/reserve`).
3. **Failure Ingestion:** Stage 4 returns `HTTP 503 Service Unavailable` with `duration_ms: 350`.
4. **Deterministic Detection:** `detector.py` catches `event.http_status == 503`:
   - Creates `Incident` record (`incident_status: "DETECTED"`, `failure_category: "API_ERROR"`, `severity: "LOW"`, `retry_count: 0`, `max_retries: 3`).
   - Order remains in `order_status: "PROCESSING"` (never marked failed prematurely).
5. **Advisory RCA Generation:** `gemini_rca.py` generates an advisory diagnosis:
   - Root cause: *"Transient database connection pool starvation on inventory replica node."*
   - Recommended action: `RETRY_WITH_BACKOFF`.
   - Risk level: `LOW`. Confidence: `HIGH`.
6. **Policy Authorization:** `policy_engine.evaluate_action()` inspects the incident:
   - Verifies retries ($0 < 3$).
   - Verifies stage (`INVENTORY` is not a privileged stage like `PAYMENT`).
   - Calculates backoff: $2^{(1 - 1)} = 1\text{ second}$.
   - Authorizes retry.
7. **Idempotent Retry Execution:** `resolution_service.execute_resolution()` generates an idempotency key `IDEMP-INC-...-ATTEMPT-1` and dispatches the retry to `simulator.reserve_inventory()`. The simulator succeeds with HTTP 200.
8. **Downstream State Verification:** `resolution_service` calls `simulator.verify_inventory_reservation(order_id)`:
   - Confirms internal simulator inventory allocation status is `"RESERVED"`.
   - Transitions incident to `incident_status: "RESOLVED"`.
9. **Journey Continuation:** `resolution_service` queues background continuation via FastAPI `BackgroundTasks`. The background worker executes stages 5 (`FULFILMENT`), 6 (`DELIVERY`), and 7 (`NOTIFICATION`).
10. **Final State:** Order transitions to `COMPLETED`.

### 3.2 Expected Behaviors & State Changes
- **UI Behavior:** In View B, Stage 4 displays an initial red `HTTP 503` badge, followed by a green self-healing resolution badge. The RCA panel renders the root cause narrative and confidence badge. The order advances to `COMPLETED`.
- **Database Changes:**
  - 1 row in `orders` (`order_status = "COMPLETED"`).
  - 8+ rows in `order_events` (including 1 failed event with `http_status = 503` and 1 successful retry with `http_status = 200`).
  - 1 row in `incidents` (`incident_status = "RESOLVED"`, `retry_count = 1`).
  - 1 row in `rca_reports` (`recommended_action = "RETRY_WITH_BACKOFF"`).
  - 1 row in `resolution_actions` (`verification_passed = True`, `execution_status = "SUCCEEDED"`).
- **Audit Events:** `ORDER_INGESTED`, `INCIDENT_DETECTED`, `RCA_COMPLETED`, `RESOLUTION_AUTHORIZED`, `RESOLUTION_EXECUTED`, `VERIFICATION_PASSED`, `INCIDENT_RESOLVED`, `ORDER_COMPLETED`.
- **Common Failure Conditions:** If downstream verification fails (e.g. simulated inventory rollback), the system blocks completion, flags `INCIDENT_ESCALATED`, and retains the order in `PROCESSING`.

---

## 4. Scenario 2: Fulfilment SLA Delay & Operator Alert (`SCENARIO_2_SLA_DELAY`)

### 4.1 Technical Workflow
1. **Trigger:** Dispatched with `scenario_key: "SCENARIO_2_SLA_DELAY"`.
2. **Execution up to Fulfilment:** Stages 1 to 4 execute cleanly with HTTP 200.
3. **Fault Injection & Latency Simulation:** At Stage 5 (`FULFILMENT`), the simulator injects a 10,000ms delay representing warehouse picking station conveyor backpressure.
4. **SLA Evaluation:** `detector.py` invokes `evaluate_stage_sla(stage="FULFILMENT", duration_ms=10000)`:
   - Queries `system_policies` for `SLA_STAGE_FULFILMENT_MS` (configured baseline: 5000ms).
   - Calculates breach: $10,000\text{ms} - 5,000\text{ms} = 5,000\text{ms}$ breach.
5. **Incident Creation & Order Flagging:**
   - Creates `Incident` record (`failure_category: "ORDER_DELAY"`, `failure_type: "SLA_BREACH"`, `severity: "MEDIUM"`).
   - Transitions order status to `order_status: "DELAYED"`.
6. **Advisory RCA Diagnosis:**
   - Root cause: *"Warehouse picking station queue congestion and packaging conveyor backpressure."*
   - Recommended action: `EXPEDITE_FULFILMENT`.
7. **Policy Boundary Constraints (Safety Controls):**
   - **Rule 4 Enforcement:** If an automated actor attempts `CANCEL_ORDER` or `AUTOMATIC_CANCELLATION`, the Policy Engine blocks it with a policy violation error.
   - **Rule 4 Enforcement:** Blind technical retries (`RETRY_WITH_BACKOFF`) are prohibited because the operation is not failing with a technical error code.
   - **Authorized Action:** Only non-destructive priority queue expedition (`EXPEDITE_FULFILMENT`) is authorized.
8. **Final State:** The order remains flagged as `DELAYED` pending manual operator investigation or priority expedition dispatch.

### 4.2 Expected Behaviors & State Changes
- **UI Behavior:** View A displays the order with an amber `DELAYED` badge. View B renders a yellow alert banner detailing the stage, actual duration (10,000ms), and SLA threshold (5,000ms).
- **Database Changes:**
  - 1 row in `orders` (`order_status = "DELAYED"`).
  - 5 rows in `order_events` (Stage 5 recorded with `duration_ms = 10000`, `event_status = "DELAYED"`).
  - 1 row in `incidents` (`failure_category = "ORDER_DELAY"`, `failure_type = "SLA_BREACH"`).
- **Audit Events:** `ORDER_INGESTED`, `INCIDENT_DETECTED`, `SLA_BREACH_DETECTED`, `OPERATOR_ALERT_ISSUED`.
- **Common Failure Conditions:** Automatic cancellation triggered by external scripts is rejected with HTTP 400.

---

## 5. Scenario 3: Hard Business Rejection & Human-in-the-Loop Approval (`SCENARIO_3_HARD_REJECTION`)

### 5.1 Technical Workflow
1. **Trigger:** Dispatched with `scenario_key: "SCENARIO_3_HARD_REJECTION"`.
2. **Clean Initial Execution:** Stages 1, 2, and 3 (Order, Address, Payment) succeed cleanly. Payment is captured and funds are settled.
3. **Business Rejection Injection:** At Stage 4 (`INVENTORY`), the simulator simulates that product SKU `SKU-CYBER-500` is depleted. Returns `HTTP 422 Unprocessable Entity` with error message `"Out of stock at primary distribution hub"`.
4. **Deterministic Classification:** `detector.py` classifies the HTTP 422 as a permanent business rejection:
   - Creates `Incident` (`failure_category: "ORDER_REJECTION"`, `failure_type: "OUT_OF_STOCK"`, `severity: "HIGH"`).
   - Order remains in `order_status: "PROCESSING"` (inventory blocked).
5. **Policy Retry Prohibition:** `policy_engine.py` Rule 5 strictly prohibits automated technical retries for permanent out-of-stock rejections.
6. **Human Approval Queue Routing:**
   - Creates `OperatorApproval` entity (`decision: "PENDING"`, `risk_level: "HIGH"`, timeout: 600 seconds).
   - Incident transitions to `incident_status: "PENDING_APPROVAL"`.
7. **Operator Decision (View C):**
   - The human operator reviews the incident in the Human Approval Queue.
   - **Approval Path:** Operator inputs substitute SKU (e.g. `SKU-CYBER-500-ALT`) and alternate warehouse hub (e.g. `HUB-EAST-02`), and clicks **Approve & Reallocate**.
   - `approval_service.py` validates both parameters, updates inventory allocation in the simulator, verifies the downstream reservation, transitions the approval to `APPROVED`, resolves the incident, and resumes remaining stages to `COMPLETED`.
   - **Rejection Path:** Operator selects **Reject Order** and clicks submit. The system sends `selected_action: "REJECT_ORDER"`, marks the approval `REJECTED`, and transitions the order to `FAILED`.

### 5.2 Expected Behaviors & State Changes
- **UI Behavior:** Navigation bar badge increments the pending approvals count. View C displays the order in the approval table with a red `HIGH RISK` badge. Entering valid substitution parameters and submitting approval displays a green verification banner.
- **Database Changes (Approval Path):**
  - 1 row in `operator_approvals` (`decision = "APPROVED"`, `selected_action = "SUBSTITUTE_SKU_AND_REALLOCATE"`).
  - 1 row in `incidents` (`incident_status = "RESOLVED"`).
  - 1 row in `orders` (`order_status = "COMPLETED"`, `inventory_status = "RESERVED"`).
- **Database Changes (Rejection Path):**
  - 1 row in `operator_approvals` (`decision = "REJECTED"`, `selected_action = "REJECT_ORDER"`).
  - 1 row in `orders` (`order_status = "FAILED"`).
- **Audit Events:** `INCIDENT_DETECTED`, `APPROVAL_REQUESTED`, `OPERATOR_APPROVED` (or `OPERATOR_REJECTED`), `VERIFICATION_PASSED`, `ORDER_COMPLETED` (or `ORDER_FAILED`).
- **Common Failure Conditions:** Submitting approval with empty substitute SKU or blank warehouse hub triggers client-side validation rejection and backend HTTP 400.

