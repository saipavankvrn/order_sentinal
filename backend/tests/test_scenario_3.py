import json
import pytest
from fastapi.testclient import TestClient
from backend.app.models.order import Order, Incident, OperatorApproval
from backend.app.services.simulator import simulator
from backend.app.policies.policy_engine import policy_engine
from backend.app.db.session import SessionLocal


def test_policy_blocks_hard_rejection_auto_retry():
    """Verifies that the deterministic policy engine strictly forbids automated retries
    and requires Human-in-the-Loop approval for hard business rejections (OUT_OF_STOCK / HTTP_422).
    """
    mock_incident = Incident(
        incident_id="INC-REJECT-01",
        order_id="ORD-REJECT-01",
        stage="INVENTORY",
        service_name="inventory_service",
        failure_category="ORDER_REJECTION",
        failure_type="OUT_OF_STOCK",
        retry_count=0,
        max_retries=0
    )

    # 1. Blind technical retry prohibited
    auth, reason, backoff, esc = policy_engine.evaluate_action(
        mock_incident, "RETRY_WITH_BACKOFF"
    )
    assert auth is False
    assert "prohibited" in reason.lower()
    assert "human approval required" in reason.lower()
    assert backoff == 0
    assert esc is False

    # 2. Automated substitute prohibited without human decision
    auth2, reason2, _, _ = policy_engine.evaluate_action(
        mock_incident, "SUBSTITUTE_SKU_AND_REALLOCATE"
    )
    assert auth2 is False
    assert "human approval" in reason2.lower()


def test_scenario_3_hitl_loop(client: TestClient):
    """Full integration test for Milestone 3 Scenario 3:
    1. Ingests order and simulates HTTP 422 Out-of-Stock rejection at Inventory.
    2. Failure detected: order remains in PROCESSING (stage blocked at INVENTORY).
    3. Incident created with PENDING_APPROVAL status and HIGH severity.
    4. Advisory RCA generated with HIGH risk recommending SUBSTITUTE_SKU_AND_REALLOCATE.
    5. Queued in Human Approval Queue with PENDING decision.
    6. Operator approves substitution with substitute SKU and alternate warehouse hub.
    7. Parameter validation succeeds and adapter executes substitution.
    8. Downstream domain state verification confirms reservation.
    9. Incident transitions to RESOLVED; order returns to PROCESSING.
    10. Background continuation completes stages 5, 6, and 7 to COMPLETED.
    """
    # Step 1: Trigger Scenario 3
    init_resp = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={
            "scenario_key": "SCENARIO_3_HARD_REJECTION",
            "customer_name": "Sarah Connor",
            "product_sku": "SKU-CYBER-500",
            "order_amount": 199.99
        }
    )
    assert init_resp.status_code == 200
    payload = init_resp.json()
    assert payload["success"] is True
    data = payload["data"]

    order = data["order"]
    incident = data["incident"]
    rca = data["rca"]
    approval = data["approval"]

    # Assert initial order state: PROCESSING, INVENTORY stage blocked, inventory_status REJECTED
    assert order["order_status"] == "PROCESSING"
    assert order["current_stage"] == "INVENTORY"
    assert order["inventory_status"] == "REJECTED"
    assert order["payment_status"] == "CAPTURED"

    # Assert incident: ORDER_REJECTION, OUT_OF_STOCK, PENDING_APPROVAL
    assert incident["failure_category"] == "ORDER_REJECTION"
    assert incident["failure_type"] == "OUT_OF_STOCK"
    assert incident["incident_status"] == "PENDING_APPROVAL"
    assert incident["severity"] == "HIGH"

    # Assert RCA: HIGH risk, SUBSTITUTE_SKU_AND_REALLOCATE recommended
    assert rca["recommended_action"] == "SUBSTITUTE_SKU_AND_REALLOCATE"
    assert rca["risk_level"] == "HIGH"
    assert rca["evidence_strength"] in ["HIGH", "MEDIUM"]

    # Assert Approval queued
    assert approval is not None
    assert approval["decision"] == "PENDING"
    assert approval["selected_action"] == "SUBSTITUTE_SKU_AND_REALLOCATE"
    approval_id = approval["approval_id"]

    # Step 2: Query Pending Approvals Queue API
    pending_resp = client.get("/api/v1/approvals/pending")
    assert pending_resp.status_code == 200
    pending_list = pending_resp.json()["data"]
    assert any(a["approval_id"] == approval_id for a in pending_list)

    # Step 3: Operator Submits APPROVED decision with valid substitution parameters
    decide_resp = client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={
            "decision": "APPROVED",
            "operator_id": "OP-JATAYU-01",
            "operator_name": "Devin Lead",
            "operator_notes": "Stock replenished at alternate hub. Safe to substitute.",
            "selected_action": "SUBSTITUTE_SKU_AND_REALLOCATE",
            "action_parameters": {
                "substitute_sku": "SKU-CYBER-500-ALT",
                "alternate_hub": "HUB-EAST-02"
            }
        }
    )
    assert decide_resp.status_code == 200
    decide_data = decide_resp.json()["data"]

    # Assert decision response contracts per API_SPECIFICATION.md
    assert decide_data["approval_id"] == approval_id
    assert decide_data["decision"] == "APPROVED"
    assert decide_data["execution_status"] == "SUCCEEDED"
    assert decide_data["verification_passed"] is True
    assert decide_data["order_status"] == "PROCESSING"
    assert decide_data["current_stage"] == "FULFILMENT"

    # Step 4: Verify Incident is RESOLVED
    inc_resp = client.get(f"/api/v1/incidents/{incident['incident_id']}")
    assert inc_resp.status_code == 200
    assert inc_resp.json()["data"]["incident"]["incident_status"] == "RESOLVED"

    # Step 5: Verify Order Completed across all 7 stages via background continuation
    order_resp = client.get(f"/api/v1/orders/{order['order_id']}")
    assert order_resp.status_code == 200
    order_final = order_resp.json()["data"]
    assert order_final["order_status"] == "COMPLETED"
    assert order_final["product_sku"] == "SKU-CYBER-500-ALT"  # Substituted SKU persisted
    assert order_final["inventory_status"] == "RESERVED"

    # Verify Journey shows all 7 stages succeeded
    journey_resp = client.get(f"/api/v1/orders/{order['order_id']}/journey")
    assert journey_resp.status_code == 200
    stages = journey_resp.json()["data"]["stages"]
    assert len(stages) == 7
    for stg in stages:
        assert stg["status"] == "SUCCESS"

    # Step 6: Verify Audit Trail
    audit_resp = client.get(f"/api/v1/audit?order_id={order['order_id']}")
    assert audit_resp.status_code == 200
    event_types = [l["event_type"] for l in audit_resp.json()["data"]]
    assert "INCIDENT_DETECTED" in event_types
    assert "APPROVAL_REQUESTED" in event_types
    assert "OPERATOR_APPROVED" in event_types
    assert "VERIFICATION_PASSED" in event_types
    assert "INCIDENT_RESOLVED" in event_types
    assert "ORDER_COMPLETED" in event_types


def test_operator_approval_validation_and_verify(client: TestClient):
    """Verifies that the simulated inventory adapter validates substitution parameters,
    executes substitution, and confirms actual domain store state mutation.
    """
    init_resp = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={"scenario_key": "SCENARIO_3_HARD_REJECTION"}
    )
    assert init_resp.status_code == 200
    approval_id = init_resp.json()["data"]["approval"]["approval_id"]
    order_id = init_resp.json()["data"]["order"]["order_id"]

    # Submit valid parameters
    resp = client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={
            "decision": "APPROVED",
            "operator_id": "OP-02",
            "operator_name": "Alex Vance",
            "selected_action": "SUBSTITUTE_SKU_AND_REALLOCATE",
            "action_parameters": {
                "substitute_sku": "SKU-CYBER-500-ALT",
                "alternate_hub": "HUB-WEST-01"
            }
        }
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["verification_passed"] is True
    assert resp.json()["data"]["execution_status"] == "SUCCEEDED"

    # Assert domain store state directly
    verified, details = simulator.verify_inventory_state(order_id)
    assert verified is True
    assert "SKU-CYBER-500-ALT" in details
    assert "HUB-WEST-01" in details


def test_operator_rejection_fails_order(client: TestClient):
    """Verifies that an operator REJECTED decision:
    - Marks approval REJECTED.
    - Marks incident REJECTED.
    - Transitions order to FAILED.
    - Dispatches no retry or substitution.
    - Emits audit events OPERATOR_REJECTED and ORDER_FAILED.
    """
    init_resp = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={"scenario_key": "SCENARIO_3_HARD_REJECTION"}
    )
    assert init_resp.status_code == 200
    approval_id = init_resp.json()["data"]["approval"]["approval_id"]
    incident_id = init_resp.json()["data"]["incident"]["incident_id"]
    order_id = init_resp.json()["data"]["order"]["order_id"]

    # Operator decides REJECTED
    reject_resp = client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={
            "decision": "REJECTED",
            "operator_id": "OP-01",
            "operator_name": "Devin Lead",
            "operator_notes": "No alternate stock available and substitution refused by customer."
        }
    )
    assert reject_resp.status_code == 200
    data = reject_resp.json()["data"]

    # Assert decision response
    assert data["decision"] == "REJECTED"
    assert data["order_status"] == "FAILED"
    assert data["verification_passed"] is False

    # Assert Incident is REJECTED
    inc_resp = client.get(f"/api/v1/incidents/{incident_id}")
    assert inc_resp.status_code == 200
    assert inc_resp.json()["data"]["incident"]["incident_status"] == "REJECTED"

    # Assert Order is FAILED
    order_resp = client.get(f"/api/v1/orders/{order_id}")
    assert order_resp.status_code == 200
    assert order_resp.json()["data"]["order_status"] == "FAILED"
    assert order_resp.json()["data"]["inventory_status"] == "REJECTED"

    # Assert Audit Trail contains OPERATOR_REJECTED and ORDER_FAILED
    audit_resp = client.get(f"/api/v1/audit?order_id={order_id}")
    assert audit_resp.status_code == 200
    event_types = [l["event_type"] for l in audit_resp.json()["data"]]
    assert "OPERATOR_REJECTED" in event_types
    assert "ORDER_FAILED" in event_types


def test_invalid_substitute_sku_rejection(client: TestClient):
    """Verifies that providing an invalid substitute SKU (not starting with SKU- or identical to depleted SKU)
    is rejected with HTTP 400 Bad Request and does not execute substitution.
    """
    init_resp = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={"scenario_key": "SCENARIO_3_HARD_REJECTION", "product_sku": "SKU-CYBER-500"}
    )
    assert init_resp.status_code == 200
    approval_id = init_resp.json()["data"]["approval"]["approval_id"]

    # Case 1: Malformed SKU format (does not start with SKU-)
    bad_resp1 = client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={
            "decision": "APPROVED",
            "operator_id": "OP-01",
            "operator_name": "Devin Lead",
            "action_parameters": {
                "substitute_sku": "INVALID-FORMAT",
                "alternate_hub": "HUB-EAST-02"
            }
        }
    )
    assert bad_resp1.status_code == 400
    assert "Invalid substitute SKU" in bad_resp1.json()["detail"]

    # Case 2: Identical depleted SKU
    bad_resp2 = client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={
            "decision": "APPROVED",
            "operator_id": "OP-01",
            "operator_name": "Devin Lead",
            "action_parameters": {
                "substitute_sku": "SKU-CYBER-500",
                "alternate_hub": "HUB-EAST-02"
            }
        }
    )
    assert bad_resp2.status_code == 400
    assert "identical depleted SKU" in bad_resp2.json()["detail"]


def test_invalid_alternate_warehouse_rejection(client: TestClient):
    """Verifies that providing an invalid warehouse hub identifier (not starting with HUB-)
    is rejected with HTTP 400 Bad Request.
    """
    init_resp = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={"scenario_key": "SCENARIO_3_HARD_REJECTION"}
    )
    assert init_resp.status_code == 200
    approval_id = init_resp.json()["data"]["approval"]["approval_id"]

    bad_resp = client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={
            "decision": "APPROVED",
            "operator_id": "OP-01",
            "operator_name": "Devin Lead",
            "action_parameters": {
                "substitute_sku": "SKU-CYBER-500-ALT",
                "alternate_hub": "SOME_RANDOM_LOCATION"
            }
        }
    )
    assert bad_resp.status_code == 400
    assert "Invalid alternate warehouse hub" in bad_resp.json()["detail"]


def test_failed_downstream_verification_blocks_recovery(client: TestClient, monkeypatch):
    """Verifies that if substitution returns HTTP 200 but downstream state verification
    probe fails (domain store unconfirmed), recovery is blocked, the incident remains open,
    and subsequent stages are not resumed.
    """
    init_resp = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={"scenario_key": "SCENARIO_3_HARD_REJECTION"}
    )
    assert init_resp.status_code == 200
    approval_id = init_resp.json()["data"]["approval"]["approval_id"]
    incident_id = init_resp.json()["data"]["incident"]["incident_id"]
    order_id = init_resp.json()["data"]["order"]["order_id"]

    # Mock verify_inventory_state to simulate domain record missing
    monkeypatch.setattr(
        simulator,
        "verify_inventory_state",
        lambda oid: (False, "Probe failed: Reservation unconfirmed in domain store.")
    )

    resp = client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={
            "decision": "APPROVED",
            "operator_id": "OP-01",
            "operator_name": "Devin Lead",
            "action_parameters": {
                "substitute_sku": "SKU-CYBER-500-ALT",
                "alternate_hub": "HUB-EAST-02"
            }
        }
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["verification_passed"] is False
    assert data["execution_status"] == "FAILED"

    # Incident must NOT be RESOLVED
    inc_resp = client.get(f"/api/v1/incidents/{incident_id}")
    assert inc_resp.status_code == 200
    assert inc_resp.json()["data"]["incident"]["incident_status"] != "RESOLVED"

    # Order must NOT be COMPLETED
    order_resp = client.get(f"/api/v1/orders/{order_id}")
    assert order_resp.status_code == 200
    assert order_resp.json()["data"]["order_status"] != "COMPLETED"


def test_duplicate_approval_request_does_not_execute_substitution_twice(client: TestClient):
    """Verifies that resubmitting the identical approved decision returns cached HTTP 200
    without executing duplicate substitution, and conflicting decision returns HTTP 409 Conflict.
    """
    init_resp = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={"scenario_key": "SCENARIO_3_HARD_REJECTION"}
    )
    assert init_resp.status_code == 200
    approval_id = init_resp.json()["data"]["approval"]["approval_id"]

    body = {
        "decision": "APPROVED",
        "operator_id": "OP-01",
        "operator_name": "Devin Lead",
        "action_parameters": {
            "substitute_sku": "SKU-CYBER-500-ALT",
            "alternate_hub": "HUB-EAST-02"
        }
    }

    # Dispatch 1: First decision
    first_resp = client.post(f"/api/v1/approvals/{approval_id}/decide", json=body)
    assert first_resp.status_code == 200
    assert first_resp.json()["data"]["decision"] == "APPROVED"

    # Dispatch 2: Duplicate replay -> returns cached 200 with idempotent message
    replay_resp = client.post(f"/api/v1/approvals/{approval_id}/decide", json=body)
    assert replay_resp.status_code == 200
    assert replay_resp.json()["data"]["decision"] == "APPROVED"
    assert "idempotent replay" in replay_resp.json()["message"].lower()

    # Dispatch 3: Conflicting decision -> returns HTTP 409 Conflict
    conflict_body = {"decision": "REJECTED", "operator_id": "OP-01", "operator_name": "Devin Lead"}
    conflict_resp = client.post(f"/api/v1/approvals/{approval_id}/decide", json=conflict_body)
    assert conflict_resp.status_code == 409
    assert "Conflicting decision rejected" in conflict_resp.json()["detail"]


def test_override_decision_prohibited(client: TestClient):
    """Verifies that submitting OVERRIDE as a decision returns HTTP 400 Bad Request
    since override functionality is excluded from the approved MVP scope.
    """
    init_resp = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={"scenario_key": "SCENARIO_3_HARD_REJECTION"}
    )
    assert init_resp.status_code == 200
    approval_id = init_resp.json()["data"]["approval"]["approval_id"]

    override_resp = client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={
            "decision": "OVERRIDE",
            "operator_id": "OP-01",
            "operator_name": "Devin Lead"
        }
    )
    assert override_resp.status_code == 400
    assert "OVERRIDE is excluded from MVP scope" in override_resp.json()["detail"]


def test_pending_approvals_api(client: TestClient):
    """Verifies GET /api/v1/approvals/pending and GET /api/v1/approvals/{approval_id} endpoints."""
    init_resp = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={"scenario_key": "SCENARIO_3_HARD_REJECTION"}
    )
    assert init_resp.status_code == 200
    approval_id = init_resp.json()["data"]["approval"]["approval_id"]

    # Test GET pending
    pending_resp = client.get("/api/v1/approvals/pending")
    assert pending_resp.status_code == 200
    items = pending_resp.json()["data"]
    match = next((a for a in items if a["approval_id"] == approval_id), None)
    assert match is not None
    assert match["risk_level"] == "HIGH"
    assert match["decision"] == "PENDING"
    assert match["order"] is not None

    # Test GET detail
    detail_resp = client.get(f"/api/v1/approvals/{approval_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()["data"]
    assert detail["approval_id"] == approval_id
    assert detail["incident_id"] == match["incident_id"]


def test_scenario_3_ui_markers(client: TestClient):
    """Verifies that the UI dashboard endpoint at /ui renders the dedicated Human Approval Queue
    elements for Milestone 3.
    """
    resp = client.get("/ui")
    assert resp.status_code == 200
    text = resp.text
    assert "Human-in-the-Loop Approval Queue" in text
    assert "HIGH RISK" in text
    assert "substituteSkuInput" in text
    assert "alternateHubInput" in text
    assert "Approve Substitution" in text
    assert "Reject Order" in text
    assert "SCENARIO_3_HARD_REJECTION" in text

