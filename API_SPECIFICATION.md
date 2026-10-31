# REST API Specification Document
## OrderFlow Sentinel — Backend OpenAPI & Interface Contract

---

### Document Control
- **Document Version:** 1.2.1 (Scope Freeze Baseline with Lifecycle, Approval & Type Harmonization)
- **Status:** Approved for Implementation Planning
- **Base URL:** `http://localhost:8000/api/v1`
- **Interactive Documentation:** `http://localhost:8000/docs` (Swagger UI), `http://localhost:8000/redoc` (ReDoc)
- **Content Type:** `application/json`
- **Context:** Virtusa Jatayu Forward Deployed Engineer Hackathon

---

## 1. Overview & Standard Conventions

### 1.1 Standard Response Envelopes
All responses adhere strictly to standardized Pydantic JSON structure:

```json
{
  "success": true,
  "data": { ... },
  "message": "Operation completed successfully",
  "timestamp": "2026-10-30T22:30:00.000Z"
}
```

Standard Error Envelope:
```json
{
  "success": false,
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Order with ID ORD-2026-1001 was not found",
    "details": {}
  },
  "timestamp": "2026-10-30T22:30:00.000Z"
}
```

### 1.2 Common HTTP Status Codes
- `200 OK`: Request processed successfully.
- `201 Created`: Resource successfully created.
- `400 Bad Request`: Validation failure or invalid parameter.
- `404 Not Found`: Target resource not found.
- `409 Conflict`: Duplicate idempotency key reused with a conflicting action/payload.
- `422 Unprocessable Entity`: Schema validation error.
- `500 Internal Server Error`: Unexpected internal exception.

---

## 2. API Endpoints by Domain

---

### 2.1 System Health & Diagnostics (`/api/v1/health`)

#### 1. System Health Check
- **Route:** `GET /health`
- **Description:** Verifies SQLite database connectivity and schema readiness. Gemini connectivity is reported as an optional dependency; the application remains fully healthy even if Gemini credentials are unconfigured or unavailable. The active model ID is derived at runtime from `GEMINI_MODEL_ID`. Secrets (`GEMINI_API_KEY`) are never exposed.
- **Response `200 OK`:**
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
      "gemini_available": true,
      "model_configured": "configured-gemini-model",
      "fallback_mode": false
    },
    "uptime_seconds": 3410
  },
  "message": "System is healthy and operational",
  "timestamp": "2026-10-30T22:30:00.000Z"
}
```

---

### 2.2 Module A: Order Management (`/api/v1/orders`)

#### 1. List Orders
- **Route:** `GET /orders`
- **Query Parameters:**
  - `page` (int, default: 1)
  - `limit` (int, default: 20)
  - `status` (`PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`, `DELAYED`, `CANCELLED`)
  - `search` (string, optional: order_id, customer_name, product_name)
- **Response `200 OK`:**
```json
{
  "success": true,
  "data": {
    "total": 45,
    "page": 1,
    "limit": 20,
    "items": [
      {
        "order_id": "ORD-2026-1001",
        "correlation_id": "corr-uuid-9102",
        "customer_id": "CUST-4091",
        "customer_name": "Sarah Connor",
        "customer_email": "sarah.connor@example.com",
        "product_sku": "SKU-CYBER-500",
        "product_name": "High-Performance Fiber Gateway",
        "order_amount": 199.99,
        "currency": "USD",
        "current_stage": "INVENTORY",
        "order_status": "PROCESSING",
        "payment_status": "CAPTURED",
        "inventory_status": "PENDING",
        "fulfilment_status": "PENDING",
        "created_at": "2026-10-30T21:40:00Z",
        "updated_at": "2026-10-30T21:40:15Z"
      }
    ]
  }
}
```

#### 2. Get Order Details & Journey
- **Route:** `GET /orders/{order_id}`
- **Response `200 OK`:** Full Order object with correlated events, current stage, and incident references. Recoverable orders show `order_status: "PROCESSING"`.

#### 3. Create Synthetic Order
- **Route:** `POST /orders`
- **Request Body:**
```json
{
  "customer_name": "Alex Murphy",
  "customer_email": "alex.murphy@example.com",
  "product_sku": "SKU-DEVICE-99",
  "product_name": "5G Smart Terminal",
  "order_amount": 299.50,
  "currency": "USD"
}
```
- **Response `201 Created`:** Created order object with assigned `order_id`, `correlation_id`, and `order_status: "PENDING"`.

---

### 2.3 Module B: Journey Monitoring & Telemetry (`/api/v1/events` & `/api/v1/orders/{order_id}/journey`)

#### 1. Get Complete Order Journey Timeline
- **Route:** `GET /orders/{order_id}/journey`
- **Description:** Returns the chronological progression of all 7 stages and raw telemetry events. Updated in near-real-time via 3-second UI polling.
- **Response `200 OK`:**
```json
{
  "success": true,
  "data": {
    "order_id": "ORD-2026-1001",
    "correlation_id": "corr-uuid-9102",
    "stages": [
      {
        "stage_name": "CUSTOMER_ORDER",
        "status": "SUCCESS",
        "duration_ms": 45,
        "timestamp": "2026-10-30T21:40:01Z"
      },
      {
        "stage_name": "ADDRESS_VALIDATION",
        "status": "SUCCESS",
        "duration_ms": 112,
        "timestamp": "2026-10-30T21:40:02Z"
      },
      {
        "stage_name": "PAYMENT",
        "status": "SUCCESS",
        "duration_ms": 420,
        "timestamp": "2026-10-30T21:40:03Z"
      },
      {
        "stage_name": "INVENTORY",
        "status": "FAILED",
        "duration_ms": 350,
        "timestamp": "2026-10-30T21:40:05Z",
        "error_message": "HTTP 503: Service Unavailable"
      }
    ],
    "raw_events": [
      {
        "event_id": "EVT-8801",
        "stage": "INVENTORY",
        "service_name": "inventory_service",
        "endpoint": "/v1/inventory/reserve",
        "http_method": "POST",
        "http_status": 503,
        "duration_ms": 350,
        "event_status": "FAILED",
        "error_code": "HTTP_503_SERVICE_UNAVAILABLE",
        "error_message": "Inventory replica gateway timeout",
        "timestamp": "2026-10-30T21:40:05Z"
      }
    ]
  }
}
```

---

### 2.4 Module C: Failure Detection & Incidents (`/api/v1/incidents`)

#### 1. List Incidents
- **Route:** `GET /incidents`
- **Query Parameters:**
  - `status` (`DETECTED`, `ANALYZING`, `PENDING_APPROVAL`, `RESOLVING`, `RESOLVED`, `ESCALATED`, `REJECTED`)
  - `category` (`API_ERROR`, `ORDER_DELAY`, `ORDER_REJECTION`)
  - `severity` (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`)
- **Response `200 OK`:** Paginated list of incidents with order context.

#### 2. Get Incident Detail
- **Route:** `GET /incidents/{incident_id}`
- **Response `200 OK`:** Full incident record including RCA report and resolution history.

---

### 2.5 Module D: Advisory AI Root Cause Analysis (`/api/v1/rca`)

#### 1. Trigger or Retrieve Advisory RCA
- **Route:** `POST /rca/{incident_id}/analyze`
- **Description:** Generates or fetches the advisory diagnostic report. Uses model specified in `GEMINI_MODEL_ID` or deterministic fallback. Internal chain-of-thought is excluded; output provides a concise, evidence-grounded explanation.
- **Response `200 OK`:**
```json
{
  "success": true,
  "data": {
    "rca_id": "RCA-2026-0042",
    "incident_id": "INC-2026-1001",
    "failure_category": "API_ERROR",
    "affected_service": "inventory_service",
    "observed_evidence": [
      "Endpoint POST /v1/inventory/reserve returned HTTP 503 Service Unavailable",
      "Round-trip latency recorded at 350ms",
      "Downstream log reports transient replica backpressure"
    ],
    "probable_root_cause": "Transient database connection pool starvation on inventory replica node. Downstream service is alive but experiencing momentary backpressure.",
    "evidence_strength": "HIGH",
    "corroborating_signals_count": 3,
    "recommended_action": "RETRY_WITH_BACKOFF",
    "risk_level": "LOW",
    "explanation": "HTTP 503 is a standard transient failure code. The order has not progressed beyond inventory reservation. An exponential backoff retry with a unique idempotency key is policy-approved.",
    "model_source": "configured-gemini-model",
    "prompt_tokens": 380,
    "created_at": "2026-10-30T21:40:07Z"
  }
}
```

---

### 2.6 Module E & G: Resolution Engine & State Verification (`/api/v1/resolutions`)

#### 1. Execute Resolution Action
- **Route:** `POST /resolutions/execute`
- **Request Body:**
```json
{
  "incident_id": "INC-2026-1001",
  "action_type": "RETRY_WITH_BACKOFF",
  "idempotency_key": "idemp_ORD-2026-1001_INVENTORY_1"
}
```
- **Idempotency Response Behavior:**
  - **Repeated Request (Same Key & Same Action):** Returns the existing action record and execution result (HTTP 200) without executing again.
  - **Conflicting Request (Same Key & Different Action / Payload):** Rejects request and returns HTTP 409 Conflict.
- **Retry Semantics:** `attempt_number` strictly denotes the retry execution number (1, 2, or 3). Maximum 3 retries permitted.
- **Lifecycle Semantics:** Notice that upon verified inventory recovery, `order_status` remains in `PROCESSING` to continue remaining stages (Fulfilment, Delivery, Notification), reaching `COMPLETED` only after stage 7 succeeds.
- **Response `200 OK`:**
```json
{
  "success": true,
  "data": {
    "action_id": "ACT-2026-501",
    "incident_id": "INC-2026-1001",
    "order_id": "ORD-2026-1001",
    "action_type": "RETRY_WITH_BACKOFF",
    "attempt_number": 1,
    "backoff_delay_sec": 1,
    "execution_status": "SUCCEEDED",
    "verification_passed": true,
    "verification_details": "Inventory API returned HTTP 200 OK. Stock reservation confirmed. Incident transitioned to RESOLVED. Order continues in PROCESSING and advanced to FULFILMENT.",
    "order_status": "PROCESSING",
    "completed_at": "2026-10-30T21:40:09Z"
  }
}
```

---

### 2.7 Module F: Human-in-the-Loop Approvals (`/api/v1/approvals`)

#### 1. List Pending Approvals
- **Route:** `GET /approvals/pending`
- **Response `200 OK`:** Array of incidents requiring human operator intervention.

#### 2. Submit Operator Decision
- **Route:** `POST /approvals/{approval_id}/decide`
- **Request Body:**
```json
{
  "decision": "APPROVED",
  "operator_id": "OP-JATAYU-01",
  "operator_name": "Devin Lead",
  "operator_notes": "Verified inventory replenishment at alternate hub. Safe to reallocate.",
  "selected_action": "SUBSTITUTE_SKU_AND_REALLOCATE",
  "action_parameters": {
    "substitute_sku": "SKU-CYBER-500-ALT",
    "alternate_hub": "HUB-EAST-02"
  }
}
```
- **Lifecycle & Execution Semantics:**
  - **Validation:** The simulated inventory adapter validates `selected_action` and `action_parameters` before execution.
  - **If `APPROVED`:** Dispatches the validated action, asserts state verification, marks the incident `RESOLVED`, and keeps the order in `PROCESSING` to execute remaining stages towards `COMPLETED`.
  - **If `REJECTED`:** Incident transitions to `REJECTED`, no retry is dispatched, and order transitions to `FAILED`.
- **Response `200 OK`:**
```json
{
  "success": true,
  "data": {
    "approval_id": "APP-2026-0012",
    "incident_id": "INC-2026-1003",
    "decision": "APPROVED",
    "selected_action": "SUBSTITUTE_SKU_AND_REALLOCATE",
    "action_parameters": {
      "substitute_sku": "SKU-CYBER-500-ALT",
      "alternate_hub": "HUB-EAST-02"
    },
    "execution_status": "SUCCEEDED",
    "verification_passed": true,
    "order_status": "PROCESSING",
    "current_stage": "FULFILMENT"
  },
  "message": "Operator decision approved, parameters validated, executed, and verified. Order continues in PROCESSING."
}
```

---

### 2.8 Module H: Dashboard & Analytics (`/api/v1/analytics`)

#### 1. Get Summary Metrics
- **Route:** `GET /analytics/metrics`
- **Response `200 OK`:**
```json
{
  "success": true,
  "data": {
    "total_orders": 50,
    "completed_orders": 42,
    "failed_orders": 3,
    "delayed_orders": 2,
    "pending_approvals": 1,
    "in_progress_orders": 2
  }
}
```

#### 2. Get Failure Distribution
- **Route:** `GET /analytics/distribution`
- **Response `200 OK`:** Aggregated counts grouped by `failure_category`.

---

### 2.9 Module I: Audit Trail (`/api/v1/audit`)

#### 1. Query Audit Logs
- **Route:** `GET /audit`
- **Description:** Application-level append-only audit logging. Audit records cannot be modified or deleted through the application's exposed API.
- **Query Parameters:** `order_id`, `incident_id`, `actor_type`, `limit`, `page`.
- **Response `200 OK`:** Paginated audit trail records.

---

### 2.10 Module J: Simulation Controls (`/api/v1/simulation`)

#### 1. Trigger Demonstration Scenario
- **Route:** `POST /simulation/trigger-scenario`
- **Request Body:**
```json
{
  "scenario_key": "SCENARIO_1_HTTP_503_SELF_HEAL",
  "customer_name": "Sarah Connor",
  "product_sku": "SKU-CYBER-500",
  "order_amount": 199.99
}
```
**Supported `scenario_key` values:**
- `SCENARIO_1_HTTP_503_SELF_HEAL`: Ingests order $\rightarrow$ Simulates 503 at Inventory $\rightarrow$ Detects failure (order remains `PROCESSING`) $\rightarrow$ RCA $\rightarrow$ Policy-authorized idempotent retry with backoff $\rightarrow$ Verified inventory reservation $\rightarrow$ Order continues `PROCESSING`, finishes Fulfilment, Delivery, Notification $\rightarrow$ Order `COMPLETED` $\rightarrow$ Audit log.
- `SCENARIO_2_SLA_DELAY`: Ingests order $\rightarrow$ Simulates $10,000\text{ms}$ Fulfilment delay $\rightarrow$ SLA breach detected $\rightarrow$ Order flagged `DELAYED` $\rightarrow$ Operator alert issued without auto-cancellation.
- `SCENARIO_3_HARD_REJECTION`: Ingests order $\rightarrow$ Simulates Out-of-Stock rejection $\rightarrow$ Classified as business rejection (order remains `PROCESSING`) $\rightarrow$ Routed to Human Approval Queue $\rightarrow$ Operator approves with substitute SKU & alternate hub $\rightarrow$ Adapter validates parameters & executes $\rightarrow$ Verified reservation $\rightarrow$ Order continues `PROCESSING`, finishes remaining stages $\rightarrow$ Order `COMPLETED` $\rightarrow$ Audit log.
- `SCENARIO_0_CLEAN_RUN`: Executes all 7 stages cleanly to verify baseline operational health.

---

### 2.11 Module K: System Settings & Policy Configuration (`/api/v1/settings`)

#### 1. Get System Policies
- **Route:** `GET /settings/policies`
- **Response `200 OK`:** Full dictionary of configurable illustrative demo SLA thresholds, max retry counts (3), and backoff parameters.

#### 2. Update System Policy
- **Route:** `PUT /settings/policies/{policy_key}`
- **Request Body:**
```json
{
  "policy_value": "5000"
}
```
- **Response `200 OK`:** Updated policy record with audit log emission.

---
*End of API_SPECIFICATION.md*
