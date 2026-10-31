# OrderFlow Sentinel — Complete Architecture & Data Flow Guide

> **Target Version**: 1.2.1-live-demo  
> **Platform**: FastAPI + SQLAlchemy + SQLite (WAL Mode) + React 18 (Vite + TypeScript)  
> **Purpose**: A comprehensive technical breakdown of OrderFlow Sentinel's multi-tier architecture, state machines, self-healing lifecycle, and AI integration.

---

## 1. System Overview & Architectural Principles

OrderFlow Sentinel is designed as a **resilient, policy-governed self-healing order processing platform**. Unlike standard e-commerce platforms where a transient microservice failure or inventory mismatch results in an immediate order drop or hard crash, Sentinel detects failures in flight, consults an advisory AI root-cause analyzer, and applies deterministic, policy-approved recovery actions.

### Core Architectural Safeguards:
1. **Advisory AI Boundary**: Google Gemini is strictly **advisory**. It analyzes telemetry and recommends actions, but possesses **zero execution authority**.
2. **Deterministic Policy Gate**: All recovery recommendations must pass through the authoritative `PolicyEngine` before any mutation is applied.
3. **Idempotency & Concurrency Guards**: Every automated retry receives a cryptographically unique idempotency key to prevent double charging or duplicate fulfilment.
4. **Downstream State Verification**: No order is marked recovered until the downstream service explicitly confirms the valid business state (e.g., verifying `CHARGE_CAPTURED` or `INVENTORY_RESERVED`).
5. **Zero Data Loss & Demo Isolation**: Historical records are strictly segregated from live demonstration orders.

---

## 2. Mermaid Diagrams & Step-by-Step Walkthroughs

### Diagram 1: High-Level Frontend-to-Backend Architecture

```mermaid
flowchart TD
    subgraph Browser ["Client Tier (Browser / React 18 SPA)"]
        UI_A["View A: Dashboard & Analytics"]
        UI_B["View B: Order Journey & RCA"]
        UI_C["View C: Approvals & Audit Trail"]
        UI_D["View D: Live Demonstration Cockpit"]
        APIClient["Typed API Client (src/api/client.ts)"]
    end

    subgraph Gateway ["Web Tier (FastAPI Gateway)"]
        FastAPIApp["FastAPI Main Application (app/main.py)"]
        CORS["CORS Middleware"]
        StaticServer["Static Files Mount (/ui & /assets)"]
        APIRouter["API V1 Router (/api/v1)"]
    end

    subgraph Endpoints ["REST API Endpoints Tier"]
        EP_Orders["Orders (/orders)"]
        EP_Incidents["Incidents (/incidents)"]
        EP_RCA["Advisory RCA (/rca)"]
        EP_Resolutions["Resolutions (/resolutions)"]
        EP_Approvals["Approvals (/approvals)"]
        EP_Simulation["Simulation (/simulation)"]
        EP_Analytics["Analytics (/analytics)"]
        EP_Audit["Audit Trail (/audit)"]
    end

    subgraph CoreServices ["Application Core Services"]
        OrderSvc["Order Orchestrator (order_service.py)"]
        Simulator["Synthetic Simulator (simulator.py)"]
        Detector["Failure Detector (detector.py)"]
        GeminiRCA["Gemini RCA Engine (gemini_rca.py)"]
        PolicyEng["Deterministic Policy Engine (policy_engine.py)"]
        ResSvc["Resolution Service (resolution_service.py)"]
        ApprSvc["Approval Service (approval_service.py)"]
        AuditSvc["Audit Service (audit_service.py)"]
    end

    subgraph DataTier ["Persistence Tier (SQLite WAL Mode)"]
        DB[("orderflow_sentinel.db")]
        Tables["orders | order_events | incidents<br/>rca_reports | resolution_actions<br/>operator_approvals | audit_logs"]
    end

    UI_A & UI_B & UI_C & UI_D --> APIClient
    APIClient -->|HTTP / JSON| APIRouter
    FastAPIApp --> CORS --> APIRouter
    FastAPIApp --> StaticServer
    APIRouter --> EP_Orders & EP_Incidents & EP_RCA & EP_Resolutions & EP_Approvals & EP_Simulation & EP_Analytics & EP_Audit

    EP_Orders --> OrderSvc
    EP_Simulation --> Simulator & OrderSvc
    Simulator --> OrderSvc
    OrderSvc --> Detector
    Detector --> GeminiRCA
    GeminiRCA -.->|Advisory Finding| PolicyEng
    PolicyEng -->|Authorized Action| ResSvc
    PolicyEng -->|High Risk Action| ApprSvc
    ResSvc --> OrderSvc
    ApprSvc --> OrderSvc
    OrderSvc & Detector & ResSvc & ApprSvc --> AuditSvc
    OrderSvc & Detector & ResSvc & ApprSvc & AuditSvc --> DB
```

#### Step-by-Step Flow:
1. The operator navigates the React SPA (View A, B, C, or D).
2. The typed API client executes REST calls against `/api/v1/...` endpoints.
3. The FastAPI router validates payloads with Pydantic schemas and injects a transactional SQLAlchemy database session.
4. Core services process orders, detect anomalies, consult AI advisory models, and record all events in the SQLite database and audit log.

---

### Diagram 2: Order Processing Flow (7 Sequential Journey Stages)

```mermaid
flowchart LR
    S1["1. VALIDATION<br/>(Format & Schema Check)"] --> S2["2. INVENTORY<br/>(Stock Reservation)"]
    S2 --> S3["3. PAYMENT<br/>(Payment Gateway Charge)"]
    S3 --> S4["4. FRAUD_CHECK<br/>(Risk Scoring Engine)"]
    S4 --> S5["5. FULFILMENT<br/>(Warehouse Packing)"]
    S5 --> S6["6. DELIVERY<br/>(Carrier Dispatch)"]
    S6 --> S7["7. NOTIFICATION<br/>(Customer SMS / Email)"]

    style S1 fill:#10b981,stroke:#047857,color:#ffffff
    style S2 fill:#10b981,stroke:#047857,color:#ffffff
    style S3 fill:#10b981,stroke:#047857,color:#ffffff
    style S4 fill:#10b981,stroke:#047857,color:#ffffff
    style S5 fill:#10b981,stroke:#047857,color:#ffffff
    style S6 fill:#10b981,stroke:#047857,color:#ffffff
    style S7 fill:#10b981,stroke:#047857,color:#ffffff
```

#### Step-by-Step Order Journey:
1. **Stage 1 (VALIDATION)**: Validates SKU formats, pricing, customer details, and shipping address.
2. **Stage 2 (INVENTORY)**: Calls `inventory_service` to reserve stock. (Scenario 3 injects HTTP 422 here).
3. **Stage 3 (PAYMENT)**: Authorizes and captures credit card payment via `payment_service`. (Scenario 1 injects HTTP 503 here).
4. **Stage 4 (FRAUD_CHECK)**: Evaluates transaction velocity, geo-IP, and behavioral risk via `fraud_service`.
5. **Stage 5 (FULFILMENT)**: Dispatches pick-and-pack instruction to warehouse. (Scenario 2 injects latency SLA breach here).
6. **Stage 6 (DELIVERY)**: Integrates with logistics carrier for tracking assignment via `delivery_service`.
7. **Stage 7 (NOTIFICATION)**: Dispatches customer confirmation email/SMS via `notification_service`.
8. Once all 7 stages complete, the order status transitions from `PROCESSING` to **`COMPLETED`**.

---

### Diagram 3: Failure Detection and Self-Healing Flow (Scenario 1: HTTP 503)

```mermaid
sequenceDiagram
    autonumber
    actor Client as Operator / Simulation
    participant OrderSvc as Order Service
    participant Detector as Failure Detection Engine
    participant Gemini as Advisory Gemini RCA
    participant Policy as Deterministic Policy Engine
    participant ResSvc as Resolution Service
    participant Downstream as Simulated Payment Gateway
    participant DB as SQLite DB & Audit Log

    Client->>OrderSvc: Execute Order Journey
    OrderSvc->>Downstream: Stage 3: POST /payments/charge
    Downstream-->>OrderSvc: HTTP 503 Service Unavailable
    OrderSvc->>Detector: Telemetry Event (HTTP 503, Stage PAYMENT)
    Detector->>DB: Create Incident INC-XXXX (API_ERROR, HTTP_503, Severity: LOW)
    Detector->>Gemini: Request Advisory RCA (Payload + Telemetry)
    alt Gemini Available
        Gemini-->>Detector: Structured JSON (Action: RETRY_WITH_BACKOFF, Risk: LOW)
    else Gemini Offline / Timeout / Quota
        Detector->>Detector: Execute Deterministic Fallback Rule
    end
    Detector->>DB: Store RCAReport (Advisory)
    Detector->>Policy: Evaluate Recommendation (RETRY_WITH_BACKOFF)
    Policy-->>Detector: APPROVED (Automated retry permitted, Max: 3)
    Detector->>ResSvc: Trigger Resolution (Incident INC-XXXX)
    ResSvc->>ResSvc: Generate Idempotency Key (retry-payment-XXXX)
    ResSvc->>ResSvc: Apply Exponential Backoff Delay
    ResSvc->>Downstream: Retry Charge with Idempotency Key
    Downstream-->>ResSvc: HTTP 200 OK (Charge Captured)
    ResSvc->>Downstream: Verify Downstream State (GET /payments/verify)
    Downstream-->>ResSvc: Status Verified (CHARGE_CAPTURED)
    ResSvc->>DB: Mark Incident RESOLVED, Resolution SUCCEEDED
    ResSvc->>OrderSvc: Resume Journey from Stage 4 (FRAUD_CHECK)
    OrderSvc->>DB: Complete Stages 4-7, Mark Order COMPLETED
    ResSvc-->>Client: Return Self-Healed Order Response
```

---

### Diagram 4: Human-in-the-Loop Approval Workflow (Scenario 3: HTTP 422 Out-of-Stock)

```mermaid
sequenceDiagram
    autonumber
    actor Client as Operator
    participant OrderSvc as Order Service
    participant Detector as Failure Detection Engine
    participant Policy as Deterministic Policy Engine
    participant ApprQueue as Operator Approval Queue
    participant DB as SQLite DB & Audit Log

    Client->>OrderSvc: Trigger Scenario 3 (HTTP 422 Injection)
    OrderSvc->>OrderSvc: Stage 2: INVENTORY fails with HTTP 422 Out-of-Stock
    OrderSvc->>Detector: Telemetry Event (HTTP 422, Stage INVENTORY)
    Detector->>DB: Create Incident INC-XXXX (ORDER_REJECTION, Severity: HIGH)
    Detector->>Detector: Order remains PROCESSING (Inventory blocked)
    Detector->>Policy: Evaluate Action (SUBSTITUTE_SKU_AND_REALLOCATE)
    Policy-->>Detector: REQUIRES_HUMAN_APPROVAL (Risk: HIGH, Auto-retry BLOCKED)
    Detector->>ApprQueue: Insert OperatorApproval Record APP-XXXX (PENDING)
    Detector->>DB: Transition Incident status to PENDING_APPROVAL
    Note over Client,ApprQueue: Operator inspects View C or View D in Dashboard
    Client->>ApprQueue: Submit Decision (APPROVED, SKU: SKU-CYBER-500-ALT, Hub: HUB-EAST-02)
    ApprQueue->>Policy: Validate Parameters (Substitute SKU & Hub validation)
    Policy-->>ApprQueue: Validated Successfully
    ApprQueue->>OrderSvc: Re-reserve Inventory at HUB-EAST-02
    OrderSvc-->>ApprQueue: Verified (INVENTORY_RESERVED)
    ApprQueue->>DB: Mark Approval APPROVED, Incident RESOLVED
    ApprQueue->>OrderSvc: Resume Journey Stages 3-7
    OrderSvc->>DB: Complete Stages, Mark Order COMPLETED
```

---

### Diagram 5: Database Entity-Relationship Model

```mermaid
erDiagram
    Order ||--o{ OrderEvent : "emits"
    Order ||--o{ Incident : "experiences"
    Incident ||--o| RCAReport : "analyzed_by"
    Incident ||--o{ ResolutionAction : "resolved_by"
    Incident ||--o{ OperatorApproval : "requires"

    Order {
        string order_id PK
        string correlation_id UK
        string customer_name
        string product_sku
        numeric order_amount
        string order_status
        boolean is_demo_order
        string demo_session_id
        datetime created_at
    }

    OrderEvent {
        string event_id PK
        string order_id FK
        string stage
        string service_name
        string endpoint
        int http_status
        int duration_ms
        string event_status
        datetime timestamp
    }

    Incident {
        string incident_id PK
        string order_id FK
        string failure_category
        string failure_type
        string incident_status
        string severity
        int retry_count
        datetime detected_at
    }

    RCAReport {
        string rca_id PK
        string incident_id FK
        string probable_root_cause
        string evidence_strength
        string recommended_action
        string risk_level
        string model_source
    }

    ResolutionAction {
        string action_id PK
        string incident_id FK
        string action_type
        string idempotency_key UK
        int attempt_number
        string execution_status
        boolean verification_passed
    }

    OperatorApproval {
        string approval_id PK
        string incident_id FK
        string selected_action
        string action_parameters
        string decision
        string operator_notes
        datetime requested_at
    }

    AuditLog {
        int log_id PK
        string correlation_id
        string order_id
        string event_type
        string actor_type
        string actor_id
        string summary
        datetime timestamp
    }
```

---

### Diagram 6: Gemini Advisory Integration & Deterministic Fallback Lifecycle

```mermaid
flowchart TD
    Start["Telemetry Failure Detected<br/>(HTTP 503 / 422 / SLA Breach)"] --> Prepare["Extract Observed Evidence & Service Telemetry"]
    Prepare --> CheckKey{"Is GEMINI_API_KEY Configured?"}

    CheckKey -->|Yes| CallGemini["Call Google GenAI Client<br/>(gemini-flash-latest with 30s timeout)"]
    CheckKey -->|No| DetFallback["Activate Deterministic Fallback Engine<br/>(Deterministic Domain Rules)"]

    CallGemini --> EvalResp{"Call Succeeded?"}
    EvalResp -->|Yes: Valid JSON| ParseResp["Parse Diagnosis, Recommended Action & Risk Level"]
    EvalResp -->|No: 404/503/504/Timeout| LogWarning["Log Warning & Fallback Trigger"]
    LogWarning --> DetFallback

    ParseResp --> TagAI["Tag model_source = 'gemini-flash-latest'"]
    DetFallback --> TagDet["Tag model_source = 'DETERMINISTIC_FALLBACK'"]

    TagAI --> Gate["Submit Advisory Report to Deterministic Policy Engine"]
    TagDet --> Gate

    Gate --> Decision{"Policy Evaluation"}
    Decision -->|LOW Risk & Auto-Approved| AutoExec["Autonomous Resolution Execution"]
    Decision -->|HIGH Risk / Permanent Rejection| HumanQueue["Queue in Operator Approval Table"]
```

