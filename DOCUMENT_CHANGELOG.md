# Document Changelog
## OrderFlow Sentinel — Documentation Audit & Revision Record

---

### Record Control
- **Date:** 2026-10-30
- **Version Sequence:** 1.0.0 (Initial Draft) $\longrightarrow$ 1.1.0 (MVP Scope Freeze) $\longrightarrow$ 1.2.0 (Lifecycle, Retry & Early Frontend Baseline) $\longrightarrow$ 1.2.1 (Final Consistency Baseline)
- **Author:** Lead Solutions Architect & Technical Reviewer
- **Context:** Virtusa Jatayu Forward Deployed Engineer Hackathon

---

## 1. Overview of Revision History

- **Version 1.0.0:** Initial draft containing an unconstrained enterprise architecture, synthetic ML training pipelines (Isolation Forest, Random Forest), 8 disparate scenarios, and references to distributed infrastructure.
- **Version 1.1.0:** Formal MVP scope freeze. Converted the design to a Modular Monolith with Simulated Downstream Services and Optional Gemini Integration, froze scope to 3 core scenarios, consolidated the UI to 3 cohesive views, and introduced primary database idempotency.
- **Version 1.2.0:** Targeted baseline harmonization. Corrected post-healing progression semantics, removed hardcoded Gemini models, brought frontend integration forward to Milestone 1, standardized retry limits ($\le 3$), specified idempotency response behavior, removed undefined SLA expiry transitions, and clarified detection scope. (Consolidated into 7 distinct thematic modification areas).
- **Version 1.2.1 (Current):** Final consistency audit. Eliminated order lifecycle contradictions (order remains `PROCESSING` during recoverable failures; `FAILED` reserved for unrecoverable errors; removed `FAILED --> PROCESSING`), completed the structured human approval contract (`selected_action`, `action_parameters`), unified SQLite JSON storage to SQLAlchemy `Text`, adopted accurate migration and audit logging terminology, removed `OVERRIDE` from MVP, and harmonized retry counts.

---

## 2. Summary of Modifications for Version 1.2.1

### 2.1 Resolution of Order Lifecycle Contradictions
- **The Issue:** `FAILED` was previously defined as an unrecoverable state, yet the architecture permitted a `FAILED --> PROCESSING` transition. Furthermore, an API example depicted an active recoverable inventory incident with `order_status: "FAILED"`.
- **The Correction:**
  - Standardized that recoverable HTTP 503 errors and HTTP 422 inventory rejections do **not** make the order terminally `FAILED`.
  - The order remains in `PROCESSING` while the affected stage is blocked pending investigation and resolution.
  - Failure, investigation, and recovery are tracked independently through the linked `incident` record (`DETECTED` $\longrightarrow$ `ANALYZING` $\longrightarrow$ `RESOLVING`/`PENDING_APPROVAL` $\longrightarrow$ `RESOLVED`).
  - Upon downstream verification, the order continues its journey in `PROCESSING` through remaining stages, transitioning to `COMPLETED` only after all 7 stages succeed.
  - The `FAILED` status is reserved strictly for genuinely unrecoverable orders (e.g., operator rejection or exhausted retries). The invalid `FAILED --> PROCESSING` transition was completely removed.
  - Updated API examples in `GET /orders` and `GET /orders/{order_id}` so that active recoverable orders show `order_status: "PROCESSING"`.
- **Documents Updated:** `MVP_SCOPE.md`, `PRD.md`, `SYSTEM_ARCHITECTURE.md`, `DATABASE_SCHEMA.md`, `API_SPECIFICATION.md`, `IMPLEMENTATION_PLAN.md`.

### 2.2 Complete Human Approval API Contract
- **The Issue:** The operator approval contract did not define the parameters required by the simulated inventory adapter to execute a resolution.
- **The Correction:**
  - Standardized a structured request body:
    - `decision`: `APPROVED` | `REJECTED`
    - `operator_id`: string
    - `operator_name`: string
    - `operator_notes`: string
    - `selected_action`: string (e.g., `SUBSTITUTE_SKU_AND_REALLOCATE`)
    - `action_parameters`: object containing specific execution parameters (e.g., `substitute_sku` and `alternate_hub`).
  - Added adapter validation: The simulated adapter validates `selected_action` and `action_parameters` prior to execution.
  - Defined state branching:
    - If `APPROVED`: Action executes, state verification confirms stock reservation, incident transitions to `RESOLVED`, and order continues in `PROCESSING` towards `COMPLETED`.
    - If `REJECTED`: Incident transitions to `REJECTED`, no retry is dispatched, and order transitions to `FAILED`.
  - Updated database schema: `operator_approvals` now contains `selected_action: VARCHAR(64)` and `action_parameters: TEXT` (serialized JSON string).
- **Documents Updated:** `DATABASE_SCHEMA.md`, `API_SPECIFICATION.md`, `SYSTEM_ARCHITECTURE.md`, `PRD.md`, `MVP_SCOPE.md`, `IMPLEMENTATION_PLAN.md`.

### 2.3 Database Type Consistency & Migration Claims
- **The Issue:** Table specifications used `TEXT` for JSON fields while the migration section claimed generic JSON column types; portability claims overpromised zero-code-change migration.
- **The Correction:**
  - Standardized JSON storage strategy: All complex attributes (`payload_summary`, `observed_evidence`, `payload_diff`, `action_parameters`, `metadata_json`) are explicitly defined as SQLAlchemy `Column(Text)` storing serialized JSON strings, with parsing handled deterministically by Pydantic schemas.
  - Replaced all absolute portability claims with: *"SQLAlchemy reduces database migration effort, but database-specific behavior and queries may require adjustments."*
- **Documents Updated:** `DATABASE_SCHEMA.md`, `PRD.md`, `SYSTEM_ARCHITECTURE.md`, `MVP_SCOPE.md`.

### 2.4 Standardized Retry Terminology
- **The Issue:** Ambiguity across documents between retry counts and total HTTP request counts.
- **The Correction:**
  - Standardized that `max_retries = 3` represents three retries after the initial failed request.
  - Initial failed request: `retry_count = 0`.
  - First retry: `retry_count = 1` (`attempt_number = 1`).
  - Second retry: `retry_count = 2` (`attempt_number = 2`).
  - Third retry: `retry_count = 3` (`attempt_number = 3`).
  - Further retries are prohibited; if verification fails after retry 3, the incident transitions to `ESCALATED`.
  - Clarified that `attempt_number` in `resolution_actions` strictly denotes the retry execution sequence (1, 2, or 3), excluding the initial request.
- **Documents Updated:** `DATABASE_SCHEMA.md`, `PRD.md`, `SYSTEM_ARCHITECTURE.md`, `API_SPECIFICATION.md`, `MVP_SCOPE.md`, `IMPLEMENTATION_PLAN.md`.

### 2.5 Standardize Override Scope
- **The Issue:** `OVERRIDE` appeared intermittently in schemas and state machines without a functional requirement in the MVP.
- **The Correction:**
  - Removed `OVERRIDE` from the MVP scope across all documents.
  - Operator decisions are strictly `PENDING`, `APPROVED`, and `REJECTED`.
  - Removed `overridden_action` from `operator_approvals` table and schemas.
- **Documents Updated:** `DATABASE_SCHEMA.md`, `API_SPECIFICATION.md`, `SYSTEM_ARCHITECTURE.md`, `PRD.md`, `MVP_SCOPE.md`, `IMPLEMENTATION_PLAN.md`.

### 2.6 Accurate Audit Logging Terminology
- **The Issue:** Previous text claimed audit logs were tamper-proof, immutable, or permanently preserved.
- **The Correction:**
  - Standardized accurate terminology across all documents:
    *"Application-level append-only audit logging. Audit records cannot be modified or deleted through the application's exposed API."*
- **Documents Updated:** `PRD.md`, `SYSTEM_ARCHITECTURE.md`, `DATABASE_SCHEMA.md`, `API_SPECIFICATION.md`, `MVP_SCOPE.md`, `IMPLEMENTATION_PLAN.md`.

### 2.7 Changelog Count Harmonization
- **The Issue:** Section 1 of the v1.2.0 changelog referenced eight mandated corrections while enumerating seven thematic sections.
- **The Correction:**
  - Reconciled the historical count explanation in Section 1 and fully enumerated the seven distinct Version 1.2.1 corrections in this document.
  - Synchronized document version numbers to **Version 1.2.1** across all seven files.
- **Documents Updated:** `DOCUMENT_CHANGELOG.md`.

---
*End of DOCUMENT_CHANGELOG.md*
