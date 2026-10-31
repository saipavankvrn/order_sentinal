# OrderFlow Sentinel — API Testing Guide

**Document Version:** 1.2.1  
**Base URL:** `http://localhost:8000/api/v1`  
**Interactive Docs:** `http://localhost:8000/docs` (Swagger UI)  
**Tools:** PowerShell (`Invoke-RestMethod`) or `curl`  

---

## 1. Overview & Standard Conventions

All responses return standardized JSON envelopes matching Pydantic response models:

### Success Response Envelope:
```json
{
  "success": true,
  "data": { ... },
  "message": "Operation completed successfully",
  "timestamp": "2026-10-31T02:30:00.000Z"
}
```

### Common HTTP Status Codes:
- `200 OK`: Request succeeded.
- `400 Bad Request`: Validation failure, invalid policy action, or illegal state transition.
- `404 Not Found`: Resource ID not found.
- `409 Conflict`: Duplicate idempotency key with conflicting payload.
- `422 Unprocessable Entity`: Schema validation error.

---

## 2. API Endpoints Reference & Examples

### 2.1 System Health
- **Endpoint:** `GET /api/v1/health`
- **Description:** Verifies SQLite database connectivity, WAL mode, and AI engine fallback status.

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/health" -Method Get | ConvertTo-Json -Depth 4
```

---

### 2.2 List Orders (with Server-Side Pagination & Offset)
- **Endpoint:** `GET /api/v1/orders`
- **Query Parameters:**
  - `page` (int, default: 1)
  - `skip` (int, optional offset)
  - `limit` (int, default: 20, max: 100)
  - `status` (string, optional: `COMPLETED`, `PROCESSING`, `DELAYED`, `FAILED`, `PENDING`)
  - `search` (string, optional text search)

```powershell
# Page 1 (limit 15)
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/orders?page=1&skip=0&limit=15" -Method Get

# Page 2 (offset 15)
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/orders?page=2&skip=15&limit=15" -Method Get

# Filter by DELAYED status
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/orders?status=DELAYED&limit=10" -Method Get
```

---

### 2.3 Retrieve Specific Order
- **Endpoint:** `GET /api/v1/orders/{order_id}`
- **Description:** Retrieves core order attributes, payment status, inventory status, and timestamps.

```powershell
$orderId = "ORD-7E5A1191"
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/orders/$orderId" -Method Get | ConvertTo-Json -Depth 3
```

---

### 2.4 Retrieve Order Journey & Chronological Timeline
- **Endpoint:** `GET /api/v1/orders/{order_id}/journey`
- **Description:** Returns the 7-stage chronological order progression, stage HTTP status codes, latencies, and raw telemetry events.

```powershell
$orderId = "ORD-7E5A1191"
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/orders/$orderId/journey" -Method Get | ConvertTo-Json -Depth 5
```

---

### 2.5 List Incidents
- **Endpoint:** `GET /api/v1/incidents`
- **Query Parameters:**
  - `order_id` (string, optional: filters strictly by target order)
  - `status` (string, optional: `DETECTED`, `ANALYZING`, `RESOLVED`, `ESCALATED`)
  - `category` (string, optional: `API_ERROR`, `ORDER_DELAY`, `ORDER_REJECTION`)

```powershell
# Query incidents for a specific order
$orderId = "ORD-7E5A1191"
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/incidents?order_id=$orderId" -Method Get | ConvertTo-Json -Depth 3
```

---

### 2.6 Retrieve Incident Detail & Pre-Calculated RCA
- **Endpoint:** `GET /api/v1/incidents/{incident_id}`
- **Description:** Returns detailed incident attributes, including any existing advisory Root Cause Analysis report.

```powershell
$incidentId = "INC-1001"
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/incidents/$incidentId" -Method Get | ConvertTo-Json -Depth 4
```

---

### 2.7 Trigger Advisory RCA Analysis
- **Endpoint:** `POST /api/v1/rca/{incident_id}/analyze`
- **Description:** Evaluates evidence from recent telemetry events using the Gemini API or deterministic fallback engine.

```powershell
$incidentId = "INC-1001"
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/rca/$incidentId/analyze" -Method Post | ConvertTo-Json -Depth 4
```

---

### 2.8 Authorize Resolution Policy
- **Endpoint:** `POST /api/v1/resolutions/authorize`
- **Request Body Schema:**
  ```json
  {
    "incident_id": "INC-1001",
    "proposed_action": "RETRY_WITH_BACKOFF"
  }
  ```

```powershell
$body = @{
    incident_id = "INC-1001"
    proposed_action = "RETRY_WITH_BACKOFF"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/resolutions/authorize" -Method Post -Body $body -ContentType "application/json"
```

---

### 2.9 Execute Resolution Action
- **Endpoint:** `POST /api/v1/resolutions/execute`
- **Request Body Schema:**
  ```json
  {
    "incident_id": "INC-1001",
    "action_type": "RETRY_WITH_BACKOFF",
    "idempotency_key": "IDEMP-RETRY-001"
  }
  ```

```powershell
$body = @{
    incident_id = "INC-1001"
    action_type = "RETRY_WITH_BACKOFF"
    idempotency_key = "IDEMP-RETRY-$(Get-Random)"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/resolutions/execute" -Method Post -Body $body -ContentType "application/json"
```

---

### 2.10 Retrieve Pending Human Approvals Queue
- **Endpoint:** `GET /api/v1/approvals/pending`
- **Description:** Returns all unresolved Human-in-the-Loop approval requests with risk ratings and timeout counters.

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/approvals/pending" -Method Get | ConvertTo-Json -Depth 4
```

---

### 2.11 Submit Operator Decision (Approval with Substitution)
- **Endpoint:** `POST /api/v1/approvals/{approval_id}/decide`
- **Request Body Schema:**
  ```json
  {
    "decision": "APPROVED",
    "operator_name": "Devin Lead",
    "operator_notes": "Stock replenished at alternate hub.",
    "selected_action": "SUBSTITUTE_SKU_AND_REALLOCATE",
    "action_parameters": {
      "substitute_sku": "SKU-CYBER-500-ALT",
      "alternate_hub": "HUB-EAST-02"
    }
  }
  ```

```powershell
$approvalId = "APP-1001"
$body = @{
    decision = "APPROVED"
    operator_name = "Devin Lead"
    operator_notes = "Stock verified at alternate distribution hub."
    selected_action = "SUBSTITUTE_SKU_AND_REALLOCATE"
    action_parameters = @{
        substitute_sku = "SKU-CYBER-500-ALT"
        alternate_hub = "HUB-EAST-02"
    }
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/approvals/$approvalId/decide" -Method Post -Body $body -ContentType "application/json"
```

---

### 2.12 Submit Operator Decision (Order Rejection)
- **Endpoint:** `POST /api/v1/approvals/{approval_id}/decide`
- **Request Body Schema:**
  ```json
  {
    "decision": "REJECTED",
    "operator_name": "Devin Lead",
    "operator_notes": "Customer cancelled or no substitute available.",
    "selected_action": "REJECT_ORDER"
  }
  ```

```powershell
$approvalId = "APP-1001"
$body = @{
    decision = "REJECTED"
    operator_name = "Devin Lead"
    operator_notes = "No substitute stock available. Terminating order."
    selected_action = "REJECT_ORDER"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/approvals/$approvalId/decide" -Method Post -Body $body -ContentType "application/json"
```

---

### 2.13 Retrieve Append-Only Audit Trail
- **Endpoint:** `GET /api/v1/audit`
- **Query Parameters:**
  - `order_id` (string, optional)
  - `incident_id` (string, optional)
  - `actor_type` (string, optional: `SYSTEM`, `AI_AGENT`, `OPERATOR`, `SIMULATOR`)
  - `limit` (int, default: 50)
  - `page` (int, default: 1)

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/audit?limit=20" -Method Get | ConvertTo-Json -Depth 3
```

---

### 2.14 Trigger Scenarios via API
- **Endpoint:** `POST /api/v1/simulation/trigger-scenario`
- **Request Body Schema:**
  ```json
  {
    "scenario_key": "SCENARIO_1_HTTP_503_SELF_HEAL",
    "customer_name": "Sarah Connor",
    "product_sku": "SKU-CYBER-500",
    "order_amount": 199.99,
    "auto_resolve": true
  }
  ```

```powershell
# 1. Trigger Scenario 0 (Clean Baseline)
$s0Body = @{ scenario_key = "SCENARIO_0_CLEAN_RUN"; customer_name = "Alice Baseline" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/simulation/trigger-scenario" -Method Post -Body $s0Body -ContentType "application/json"

# 2. Trigger Scenario 1 (HTTP 503 Self-Healing)
$s1Body = @{ scenario_key = "SCENARIO_1_HTTP_503_SELF_HEAL"; customer_name = "Bob SelfHeal"; auto_resolve = $true } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/simulation/trigger-scenario" -Method Post -Body $s1Body -ContentType "application/json"

# 3. Trigger Scenario 2 (Fulfilment SLA Delay)
$s2Body = @{ scenario_key = "SCENARIO_2_SLA_DELAY"; customer_name = "Charlie Delayed" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/simulation/trigger-scenario" -Method Post -Body $s2Body -ContentType "application/json"

# 4. Trigger Scenario 3 (HTTP 422 Hard Rejection)
$s3Body = @{ scenario_key = "SCENARIO_3_HARD_REJECTION"; customer_name = "Diana Rejection" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/simulation/trigger-scenario" -Method Post -Body $s3Body -ContentType "application/json"
```

