# OrderFlow Sentinel — Scenario Workflow & Recovery Guide

> **Target Version**: 1.2.1-live-demo  
> **Core Concept**: Four distinct operational failure modes demonstrating clean execution, autonomous self-healing, operator delay alerts, and human-in-the-loop business recovery.

---

## Scenario Comparison Matrix

| Attribute | Scenario 0: Clean Run | Scenario 1: HTTP 503 Self-Heal | Scenario 2: SLA Delay Alert | Scenario 3: HITL Rejection |
|---|---|---|---|---|
| **Failure Injected** | None | HTTP 503 at Payment | Duration > 5000ms at Fulfilment | HTTP 422 Out-of-Stock at Inventory |
| **Incident Created?** | No | `API_ERROR / HTTP_503` | `ORDER_DELAY / SLA_BREACH` | `ORDER_REJECTION / OUT_OF_STOCK` |
| **Initial Order Status** | `PROCESSING` | `PROCESSING` | Transitions to `DELAYED` | Remains `PROCESSING` (Blocked) |
| **RCA Risk Level** | N/A | `LOW` | `LOW` | `HIGH` |
| **RCA Recommendation** | None | `RETRY_WITH_BACKOFF` | `EXPEDITE_FULFILMENT` | `SUBSTITUTE_SKU_AND_REALLOCATE` |
| **Policy Engine Action** | Standard progression | Authorizes auto-retry | Blocks auto-cancellation; alerts operator | Prohibits auto-retry; routes to HITL |
| **Recovery Mode** | N/A | **Autonomous Self-Healing** | **Operator Investigation** | **Operator-Authorized HITL** |
| **Downstream Verification**| Standard hops | Verifies `CHARGE_CAPTURED` | Verifies warehouse dispatch state | Verifies `INVENTORY_RESERVED` |
| **Final Order Status** | `COMPLETED` | `COMPLETED` | `DELAYED` (until operator action) | `COMPLETED` (after approval) |

---

## Detailed Scenario Walkthroughs

---

### Scenario 0: Normal Clean Order Journey

1. **Trigger**: Selected via UI dropdown or `POST /api/v1/simulation/trigger-scenario` with `scenario_key: "SCENARIO_0_CLEAN_RUN"`.
2. **Backend Handlers**: [`backend/app/services/order_service.py`](file:///d:/Virtusa Jatayu/backend/app/services/order_service.py) coordinates the 7 sequential stages.
3. **Database Mutations**:
   - Creates an `Order` row with `order_status = "PENDING"`.
   - Inserts 7 `OrderEvent` rows (one for each stage: `VALIDATION`, `INVENTORY`, `PAYMENT`, `FRAUD_CHECK`, `FULFILMENT`, `DELIVERY`, `NOTIFICATION`) with `http_status = 200` and `event_status = "SUCCESS"`.
   - Updates `Order` status to `COMPLETED`.
4. **Incident Created**: **None**.
5. **RCA**: Skipped.
6. **Policy Engine**: Approves standard sequential stage progression.
7. **Human Approval**: Not required.
8. **Downstream Verification**: Each stage confirms HTTP 200 OK before the next stage executes.
9. **Final Order Status**: **`COMPLETED`**.
10. **Frontend Display**: View B displays all 7 stepper icons in green; View A displays status badge `COMPLETED`.

---

### Scenario 1: HTTP 503 API Failure & Autonomous Self-Healing

1. **Trigger**: `scenario_key: "SCENARIO_1_HTTP_503_SELF_HEAL"`.
2. **Backend Handlers**: [`simulator.py`](file:///d:/Virtusa Jatayu/backend/app/services/simulator.py) injects HTTP 503 at Stage 3 (`PAYMENT`); [`detector.py`](file:///d:/Virtusa Jatayu/backend/app/services/detector.py) flags failure; [`resolution_service.py`](file:///d:/Virtusa Jatayu/backend/app/services/resolution_service.py) executes recovery.
3. **Database Mutations**:
   - Stage 3 emits an `OrderEvent` with `http_status = 503` and `error_code = "GATEWAY_TIMEOUT"`.
   - Inserts an `Incident` (`failure_category = "API_ERROR"`, `severity = "LOW"`, `incident_status = "DETECTED"`).
   - Inserts an `RCAReport` record.
   - Inserts a `ResolutionAction` record with unique `idempotency_key = "retry-payment-<hash>"`.
   - Upon successful retry, updates `Incident` to `RESOLVED`, sets `verification_passed = True`, and advances order to `COMPLETED`.
4. **Incident Created**: `INC-XXXX` (`API_ERROR`, `HTTP_503`).
5. **RCA Diagnosis**: Diagnoses transient network fault with `LOW` risk; recommends `RETRY_WITH_BACKOFF`.
6. **Policy Engine Decision**: Evaluates retry count against max ceiling (3); authorizes automated retry with exponential backoff.
7. **Recovery Mode**: **100% Autonomous**. No human operator intervention needed.
8. **Downstream Verification**: Before declaring recovery, Sentinel executes `GET /payments/verify` confirming downstream status `CHARGE_CAPTURED`.
9. **Final Order Status**: **`COMPLETED`**.
10. **Frontend Display**: View B displays payment stage self-heal indicator, resolution badge `SUCCEEDED`, and verified status.

---

### Scenario 2: SLA Delay Detection & Operator Alerting

1. **Trigger**: `scenario_key: "SCENARIO_2_SLA_DELAY"`.
2. **Backend Handlers**: [`simulator.py`](file:///d:/Virtusa Jatayu/backend/app/services/simulator.py) injects simulated latency (8500ms) at Stage 5 (`FULFILMENT`); [`detector.py`](file:///d:/Virtusa Jatayu/backend/app/services/detector.py) evaluates against policy SLA threshold (5000ms).
3. **Database Mutations**:
   - Order status transitions immediately from `PROCESSING` $\to$ **`DELAYED`**.
   - Inserts `OrderEvent` with `duration_ms = 8500` and `event_status = "DELAYED"`.
   - Inserts `Incident` with `failure_category = "ORDER_DELAY"`, `failure_type = "SLA_BREACH"`, `severity = "MEDIUM"`.
   - Inserts `RCAReport` diagnosing warehouse congestion.
   - Writes `AuditLog` event `OPERATOR_ALERT_ISSUED`.
4. **Incident Created**: `INC-XXXX` (`ORDER_DELAY`, `SLA_BREACH`).
5. **RCA Diagnosis**: Identifies fulfilment bottleneck; advises `EXPEDITE_FULFILMENT`.
6. **Policy Engine Decision**: **Prohibits automatic cancellation or automatic warehouse reassignment**. Issues operator alert.
7. **Recovery Mode**: **Operator-Governed**. The system keeps the order safely `DELAYED` pending manual investigation.
8. **Downstream Verification**: Verifies warehouse order state before any expedited status change.
9. **Final Order Status**: **`DELAYED`**.
10. **Frontend Display**: View B displays prominent amber warning banner:
   > *"Fulfilment latency exceeded SLA threshold by +3500ms. Order marked DELAYED. Awaiting operator review. Prohibited actions blocked."*

---

### Scenario 3: HTTP 422 Hard Business Rejection & Human-in-the-Loop Approval

1. **Trigger**: `scenario_key: "SCENARIO_3_HARD_REJECTION"`.
2. **Backend Handlers**: [`simulator.py`](file:///d:/Virtusa Jatayu/backend/app/services/simulator.py) injects HTTP 422 at Stage 2 (`INVENTORY`); [`detector.py`](file:///d:/Virtusa Jatayu/backend/app/services/detector.py) catches rejection; [`approval_service.py`](file:///d:/Virtusa Jatayu/backend/app/services/approval_service.py) manages operator authorization.
3. **Database Mutations**:
   - Inserts `OrderEvent` with `http_status = 422` (`Primary SKU Out of Stock`).
   - Order remains in **`PROCESSING`** (inventory stage blocked).
   - Inserts `Incident` (`failure_category = "ORDER_REJECTION"`, `severity = "HIGH"`, status `PENDING_APPROVAL`).
   - Inserts `OperatorApproval` record `APP-XXXX` with status `PENDING`.
   - When operator submits approval, record updates to `APPROVED`, inventory re-reserves at alternate hub, and order resumes to `COMPLETED`.
4. **Incident Created**: `INC-XXXX` (`ORDER_REJECTION`, `OUT_OF_STOCK`).
5. **RCA Diagnosis**: Flags permanent business failure with `HIGH` risk; recommends `SUBSTITUTE_SKU_AND_REALLOCATE`.
6. **Policy Engine Decision**: **Blocks automated retry**. Hard business rejections cannot self-heal without authorization. Routes to Human Approval Queue.
7. **Recovery Mode**: **Human-in-the-Loop**. Requires operator to provide substitute SKU and warehouse hub.
8. **Downstream Verification**: Verifies `INVENTORY_RESERVED` at alternate hub before resuming stages 3–7.
9. **Final Order Status**: **`COMPLETED`** (if approved) or **`FAILED`** (if rejected).
10. **Frontend Display**: Appears in View C (Pending Approvals Table) and View D with an interactive authorization form.

