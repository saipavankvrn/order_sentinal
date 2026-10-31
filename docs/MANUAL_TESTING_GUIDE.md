# OrderFlow Sentinel — Manual Testing & QA Verification Guide

> **Target Version**: 1.2.1-live-demo  
> **Platform**: Windows 11 (PowerShell)  
> **Test Suite**: 53 Pytest Tests (Backend) | 9 Native Tests (Frontend) | Manual Interactive Scenarios  

---

## 1. Automated Test Suite Execution

Before conducting manual tests, verify the automated regression suite to ensure a clean baseline:

```powershell
Set-Location "d:\Virtusa Jatayu"
powershell -ExecutionPolicy Bypass -File .\run_tests.ps1
```

### Expected Output:
```text
=== OrderFlow Sentinel: Full Regression Test Suite ===
[INFO] Persistent development DB active orders before tests: 513
[1/2] Running Backend Pytest Suite (53 Tests with DB Isolation)...
...
============================= 53 passed in 36.00s =============================
[PASS] Backend test suite passed cleanly!
[INFO] Persistent development DB active orders after tests: 513
[PASS] Database Isolation Verified: 0 synthetic test records added to persistent database.

[2/2] Running Frontend Unit Test Suite...
▶ OrderFlow Sentinel - Frontend Client & State Verification
...
✔ pass 9 | fail 0
=====================================================
[SUCCESS] All Backend and Frontend Tests Passed Cleanly!
=====================================================
```

---

## 2. Interactive Manual Test Scenarios

### Test Case 1: Normal Order Execution (Scenario 0)
- **Goal**: Confirm a clean order journey advances across all 7 stages without errors.
- **Steps**:
  1. Open [http://localhost:8000/ui](http://localhost:8000/ui) and navigate to the **Live Order Demonstration** tab.
  2. Click **Generate Unique ID**.
  3. Select **Normal Order (Scenario 0)**.
  4. Click **Create & Run Live Order Journey**.
- **Expected UI Result**: All 7 stepper stages illuminate green with `COMPLETED` badges.
- **Expected Backend Result**: 7 sequential HTTP 200 events logged in Uvicorn terminal.
- **Expected DB Result**: `orders.order_status` set to `COMPLETED`; 0 incidents created.
- **Pass/Fail Criteria**: PASS if order reaches `COMPLETED` in under 3 seconds; FAIL if any stage shows error or delay.

---

### Test Case 2: Autonomous Self-Healing (Scenario 1)
- **Goal**: Verify payment HTTP 503 is intercepted, retried with exponential backoff and idempotency key, verified downstream, and completed.
- **Steps**:
  1. In View D, click **Generate Unique ID**.
  2. Select **HTTP 503 API Failure (Scenario 1)**.
  3. Click **Create & Run Live Order Journey**.
- **Expected UI Result**: Stage 3 displays an amber retry indicator; timeline displays `HTTP 503 Gateway Timeout`, followed by `RETRY_WITH_BACKOFF` and successful recovery to `COMPLETED`.
- **Expected Backend Result**:
  - `AUDIT [INCIDENT_DETECTED] | Order: ORD-XXXX | Actor: SYSTEM:DETECTOR_ENGINE`
  - `AUDIT [RCA_COMPLETED] | Recommended RETRY_WITH_BACKOFF (LOW risk)`
  - `AUDIT [RESOLUTION_VERIFIED] | Downstream status verified (CHARGE_CAPTURED)`
- **Expected DB Result**:
  - `incidents.incident_status = "RESOLVED"`
  - `resolution_actions.verification_passed = 1`
  - `orders.order_status = "COMPLETED"`
- **Pass/Fail Criteria**: PASS if incident resolves autonomously without operator clicks.

---

### Test Case 3: SLA Delay Alerting (Scenario 2)
- **Goal**: Verify fulfilment latency exceeding SLA demo threshold marks order `DELAYED` and issues an operator alert without unauthorized mutations.
- **Steps**:
  1. In View D, select **SLA Fulfilment Delay (Scenario 2)**.
  2. Click **Create & Run Live Order Journey**.
- **Expected UI Result**: Stepper Stage 5 turns amber; an alert banner appears: *"Fulfilment latency exceeded SLA threshold. Order marked DELAYED. Awaiting operator review."*
- **Expected Backend Result**: `AUDIT [OPERATOR_ALERT_ISSUED]` logged; no auto-cancellation occurs.
- **Expected DB Result**: `orders.order_status = "DELAYED"`; `incidents.failure_type = "SLA_BREACH"`.
- **Pass/Fail Criteria**: PASS if order stays `DELAYED` and is NOT automatically cancelled or reassigned.

---

### Test Case 4: Human-in-the-Loop Substitution (Scenario 3)
- **Goal**: Verify inventory HTTP 422 blocks automated retry, generates an approval request, and resumes only after valid operator authorization.
- **Steps**:
  1. In View D, select **Inventory Out-of-Stock (Scenario 3)**.
  2. Click **Create & Run Live Order Journey**.
  3. Verify the order remains in `PROCESSING` and an inline approval card appears.
  4. Ensure substitute SKU `SKU-CYBER-500-ALT` and Hub `HUB-EAST-02` are populated.
  5. Click **Authorize Substitution**.
- **Expected UI Result**: Approval status turns to `APPROVED`; order resumes stages 3–7 to `COMPLETED`.
- **Expected Backend Result**: Downstream inventory verification passes; audit log records `APPROVAL_DECIDED`.
- **Expected DB Result**: `operator_approvals.decision = "APPROVED"`; `orders.order_status = "COMPLETED"`.
- **Pass/Fail Criteria**: PASS if substitution executes and order successfully completes.

---

### Test Case 5: 🎲 Random Demonstration Mode
- **Goal**: Verify dynamic scenario selection following the 50% Clean / 25% 503 / 15% SLA / 10% 422 distribution.
- **Steps**:
  1. In View D, select **🎲 Random Demo Mode**.
  2. Click **Create & Run Live Order Journey**.
- **Expected UI Result**: A purple banner displays the selected outcome and mathematical probability breakdown; order executes according to the chosen scenario.
- **Pass/Fail Criteria**: PASS if the scenario matches the banner announcement and executes genuinely.

---

### Test Case 6: Safe Session Reset
- **Goal**: Verify live demonstration orders are purged without altering historical records.
- **Steps**:
  1. Note the number of orders in the View D session drawer.
  2. Click **Reset Demo Session** and confirm.
- **Expected UI Result**: Live demo drawer clears to 0; fresh session ID generated.
- **Expected DB Result**: Run `SELECT COUNT(*) FROM orders;` in SQLite $\to$ count remains exactly **513**.
- **Pass/Fail Criteria**: PASS if 0 historical orders are deleted.
