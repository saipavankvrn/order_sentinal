# OrderFlow Sentinel — Project Demonstration & Interview Guide

**Document Version:** 1.2.1  
**Target Context:** Virtusa Jatayu Forward Deployed Engineer Hackathon Evaluation & Technical Deep Dives  
**Tone:** Authoritative, Professional, Engineering-Grounded  

---

## 1. The 3-Minute Executive Pitch

> *"Good morning / afternoon. I am presenting **OrderFlow Sentinel**, an enterprise-grade self-healing order failure detection and resolution platform.*
>
> *In enterprise e-commerce, customer orders traverse multiple downstream services—payment, inventory, fulfilment, logistics. When transient outages occur, naive systems often stall or perform dangerous blind retries on non-idempotent endpoints like payments. When SLA bottlenecks occur, automated rules might naively cancel orders that were already paid for. And when physical stock is depleted, technical retries are futile.*
>
> *OrderFlow Sentinel solves this with a **three-fold governance model**:*
> 1. *Deterministic Failure Detection that monitors multi-hop telemetry across all 7 journey stages.*
> 2. *Advisory AI Root Cause Analysis powered by Gemini, grounded strictly in observed telemetry evidence, with an automatic offline deterministic fallback.*
> 3. *Deterministic Policy-as-Code that enforces hard boundaries: unconstrained retries are capped at 3, blind payment re-charges are strictly prohibited, destructive order cancellations are vetoed, and permanent business stockouts are routed to a Human-in-the-Loop approval queue.*
>
> *Crucially, recovery is never declared on an HTTP 200 alone; downstream state verification guarantees the resource is reserved before an order can advance to completion.*
>
> *Let's look at the running platform."*

---

## 2. The 5-Minute Technical Demonstration Script

### Segment 1: Nominal Operations & Baseline Health (Minute 1)
1. **Show View A (Dashboard):**
   - Point out the 6 KPI cards (Total Ingested, Completed, In Progress, Delayed, Failed, Pending Approvals).
   - Point out the server-side paginated orders table and the SQLite WAL connectivity indicator in the header.
2. **Trigger Scenario 0 (Clean Baseline):**
   - Click **Scenario 0: Clean Baseline** on the persistent top control bar.
   - Point out automatic navigation to View B.
   - Watch the 7 green stage checkmarks complete: `CUSTOMER_ORDER` $\rightarrow$ `ADDRESS_VALIDATION` $\rightarrow$ `PAYMENT` $\rightarrow$ `INVENTORY` $\rightarrow$ `FULFILMENT` $\rightarrow$ `DELIVERY` $\rightarrow$ `NOTIFICATION`.
   - Explain: *"Every stage hop persists real telemetry into SQLite with HTTP status codes and millisecond duration."*

### Segment 2: Transient Self-Healing (Scenario 1) (Minute 2)
1. **Trigger Scenario 1 (HTTP 503 Self-Heal):**
   - Click **Scenario 1: HTTP 503 Self-Heal**.
   - Show Stage 4 (`INVENTORY`) fail with red `HTTP 503`.
   - Highlight: *"Notice the order is NOT marked FAILED. It remains in PROCESSING because 503 is a transient outage."*
2. **Explain Advisory RCA & Policy Engine:**
   - Point to the RCA panel: *"Gemini analyzes the telemetry and recommends `RETRY_WITH_BACKOFF`."*
   - Point to the Policy Engine: *"Policy authorizes retry attempt 1 with exponential backoff. The retry dispatches with a unique idempotency key."*
   - Show the green resolution badge and downstream state verification: *"Downstream inventory reservation is verified before remaining stages resume to COMPLETED."*

### Segment 3: Fulfilment SLA Delay & Operator Alert (Scenario 2) (Minute 3)
1. **Trigger Scenario 2 (SLA Delay):**
   - Click **Scenario 2: SLA Delay & Alert**.
   - Watch Stage 5 report 10,000ms duration.
   - Show the order transition to amber `DELAYED`.
2. **Demonstrate Policy Safety:**
   - Point to the yellow alert banner: *"The SLA threshold is 5,000ms. A 5,000ms breach occurred."*
   - Explain: *"What would a naive system do? Automatically cancel or reassign warehouses. Our Policy Engine strictly prohibits automatic cancellation or blind retries. The order remains DELAYED pending operator priority expedition."*

### Segment 4: Hard Business Rejection & Human-in-the-Loop (Scenario 3) (Minute 4)
1. **Trigger Scenario 3 (HTTP 422 Out-of-Stock):**
   - Click **Scenario 3: Hard Rejection (422)**.
   - Show Stage 4 return HTTP 422.
   - Notice the pending approvals badge in the navigation bar increment.
2. **Navigate to View C (Human Approval Queue):**
   - Point out the approval card with the red `HIGH RISK` badge and root cause explanation.
   - Explain: *"Stock is depleted. Automatic technical retries are strictly prohibited by policy rule 5."*
3. **Execute Approval:**
   - Enter substitute SKU `SKU-CYBER-500-ALT` and alternate hub `HUB-EAST-02`.
   - Click **Approve & Reallocate**.
   - Show the green verification banner: *"Downstream state verified, incident resolved, order journey resumes to COMPLETED."*

### Segment 5: Governance & Audit Trail (Minute 5)
1. **Scroll down to Application Audit Log in View C:**
   - Show the append-only audit trail.
   - Highlight the actor tags: `SIMULATOR`, `SYSTEM`, `AI_AGENT`, `OPERATOR`.
   - Point out that every resolution, policy check, and approval is immutably logged with correlation IDs and timestamps.

---

## 3. 25 Critical Technical Interview Questions & Answers

### Architecture & System Design
1. **Q: Is OrderFlow Sentinel a microservices architecture or a monolith?**  
   *A: It is engineered as a Modular Monolith with Simulated Downstream Logistics. This ensures atomic testing, zero network orchestration overhead, and high determinism during evaluation while maintaining strict domain separation.*
2. **Q: Why did you choose SQLite over PostgreSQL for this delivery?**  
   *A: SQLite in Write-Ahead Logging (WAL) mode provides zero-configuration, lightning-fast file-based persistence with full ACID compliance and concurrent read capability, perfect for hackathon evaluations and edge deployments.*
3. **Q: How does SQLite handle concurrent requests without locking?**  
   *A: By enabling `PRAGMA journal_mode=WAL;` and `check_same_thread=False` in SQLAlchemy. In WAL mode, SQLite allows unlimited concurrent readers alongside a concurrent writer without lock contention.*
4. **Q: What is the purpose of the correlation ID?**  
   *A: Every order journey is assigned a UUID correlation ID that propagates through every telemetry event, incident, resolution action, and audit log, ensuring complete cross-service distributed tracing.*

### AI & LLM Governance
5. **Q: What happens if the Gemini API key is missing or invalid?**  
   *A: The system remains fully operational. The `gemini_rca.py` engine detects the missing key or network error and immediately activates an internal deterministic rule engine providing identical structured diagnostic payloads.*
6. **Q: Can Gemini modify database records or approve actions on its own?**  
   *A: Absolutely not. The Gemini integration is strictly advisory. The LLM produces JSON diagnosis proposals. Only the deterministic Policy-as-Code engine can authorize state transitions.*
7. **Q: How do you prevent LLM hallucinations from corrupting recovery?**  
   *A: The prompt enforces strict JSON schema output with low temperature (0.1), and the Policy Engine validates all recommended action strings against a hardcoded whitelist.*
8. **Q: Which Gemini SDK and model are used?**  
   *A: Google GenAI SDK (`google-genai` v1.0.0+) with `gemini-2.0-flash` configured by default through the `GEMINI_MODEL_ID` environment variable.*

### Policy Engine & Safety Controls
9. **Q: What are the 5 core rules enforced by the Policy Engine?**  
   *A: (1) Maximum 3 retries limit; (2) Blind retry prohibition on privileged stages (Payment/Order); (3) Exponential backoff computation for technical 503 errors; (4) Veto on destructive cancellation for SLA delays; (5) Mandatory human approval gating for permanent out-of-stock rejections.*
10. **Q: Why is retrying Payment capture considered dangerous?**  
    *A: Payment endpoints are financial transactions. Blindly retrying without idempotency guarantees risks double-charging the customer's card.*
11. **Q: What is the backoff formula used for retries?**  
    *A: Exponential backoff: $2^{(\text{attempt} - 1)}$ seconds, resulting in 1s for attempt 1, 2s for attempt 2, and 4s for attempt 3.*
12. **Q: What happens if an incident exhausts all 3 retries?**  
    *A: The Policy Engine rejects further retries, and the incident is escalated to `ESCALATED` status with an audit trail event.*

### Order Journey & Scenarios
13. **Q: What are the 7 stages of an order journey?**  
    *A: `CUSTOMER_ORDER`, `ADDRESS_VALIDATION`, `PAYMENT`, `INVENTORY`, `FULFILMENT`, `DELIVERY`, `NOTIFICATION`.*
14. **Q: At what exact moment does an order transition to `COMPLETED`?**  
    *A: Only after Stage 7 (`NOTIFICATION`) successfully completes. An order is never marked completed immediately after recovering from an inventory outage.*
15. **Q: What distinguishes Scenario 1 from Scenario 3?**  
    *A: Scenario 1 is a transient technical outage (HTTP 503) that is safely self-healable via retry with backoff. Scenario 3 is a permanent business rejection (HTTP 422 Out-of-Stock) that requires human authorization of a substitute SKU.*
16. **Q: Why doesn't Scenario 2 automatically cancel the delayed order?**  
    *A: Because inventory is already reserved and payment is already captured. Cancelling an order in fulfilment creates inventory leakage and refunds without verifying warehouse physical state.*

### Downstream State Verification
17. **Q: What is downstream state verification?**  
    *A: It is an active probe verifying that the downstream microservice actually committed the state mutation (e.g. `status == "RESERVED"`), rather than relying merely on an HTTP 200 response.*
18. **Q: What happens if downstream verification fails after a retry?**  
    *A: The recovery is blocked, the incident remains un-resolved, and an `ESCALATED` event is logged to alert human operators.*

### Frontend Architecture & Integration
19. **Q: How does the frontend handle deep linking and browser refresh?**  
    *A: Via `window.history.pushState` and `window.addEventListener('popstate')`. URL parameters (`?tab=...&order_id=...`) maintain active tab and active order context across page reloads.*
20. **Q: How does the frontend handle pagination for hundreds of orders?**  
    *A: The backend supports `skip` and `limit` query parameters. View A dispatches server-side offset requests so operators can browse past the first 50 records without client memory bottlenecks.*
21. **Q: How does the frontend prevent polling race conditions?**  
    *A: `App.tsx` maintains an `isFetchingRef` guard to prevent overlapping fetch executions during the 3-second polling interval.*

### Test Isolation & Verification
22. **Q: How do you guarantee automated tests don't corrupt the development database?**  
    *A: In `backend/tests/conftest.py`, pytest initializes a temporary SQLite database using `tempfile.mkstemp()`, overrides `DATABASE_URL`, and cleans up the temporary files after the test session.*
23. **Q: How many tests are in the automated test suite?**  
    *A: 46 backend Pytest suites (all passing in under 3 seconds) and 9 frontend unit tests.*
24. **Q: How is the production frontend served by FastAPI?**  
    *A: FastAPI mounts `frontend/dist/assets` under `/assets` and serves `frontend/dist/index.html` on `/ui` via `HTMLResponse`.*
25. **Q: What are the primary future enhancements for Milestone 5?**  
    *A: Packaging into a single executable or Docker container, production Prometheus telemetry metrics, and expanded webhook alert integrations (Slack/PagerDuty).*

