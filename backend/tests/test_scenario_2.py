import json
import pytest
from fastapi.testclient import TestClient
from backend.app.models.order import Order, Incident
from backend.app.services.simulator import simulator
from backend.app.services.detector import detector
from backend.app.policies.policy_engine import policy_engine
from backend.app.db.session import SessionLocal


def test_sla_evaluator_breach():
    """Verifies that the stage SLA evaluator correctly identifies when stage latency
    exceeds the configured demo SLA threshold (10,000ms > 5,000ms).
    """
    db = SessionLocal()
    try:
        is_breach, threshold_ms, breach_ms = detector.evaluate_stage_sla(
            db=db,
            stage="FULFILMENT",
            duration_ms=10000
        )
        assert is_breach is True
        assert threshold_ms == 5000
        assert breach_ms == 5000
    finally:
        db.close()


def test_sla_evaluator_normal():
    """Verifies that the stage SLA evaluator does not flag a breach when stage latency
    remains within the allowable demo SLA threshold (450ms <= 5,000ms).
    """
    db = SessionLocal()
    try:
        is_breach, threshold_ms, breach_ms = detector.evaluate_stage_sla(
            db=db,
            stage="FULFILMENT",
            duration_ms=450
        )
        assert is_breach is False
        assert threshold_ms == 5000
        assert breach_ms == 0
    finally:
        db.close()


def test_normal_fulfilment_without_sla_breach(client: TestClient):
    """Verifies that normal fulfilment execution under 5000ms SLA threshold
    does not trigger any SLA breach, keeps the order PROCESSING, and completes cleanly.
    """
    response = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={
            "scenario_key": "SCENARIO_0_CLEAN_RUN",
            "customer_name": "Miles Dyson",
            "product_sku": "SKU-CYBER-500",
            "order_amount": 149.99
        }
    )
    assert response.status_code == 200
    data = response.json()["data"]
    order = data["order"]
    assert order["order_status"] == "COMPLETED"
    assert data["incident"] is None

    # Check journey stages
    journey_resp = client.get(f"/api/v1/orders/{order['order_id']}/journey")
    assert journey_resp.status_code == 200
    stages = journey_resp.json()["data"]["stages"]
    fulfilment_stage = next(s for s in stages if s["stage_name"] == "FULFILMENT")
    assert fulfilment_stage["status"] == "SUCCESS"
    assert fulfilment_stage["duration_ms"] < 5000


def test_scenario_2_delay_alert(client: TestClient):
    """Integration test confirming:
    - Ingests order and injects 10,000ms fulfilment latency.
    - SLA breach detected against 5,000ms demo threshold (+5,000ms breach).
    - Order transitions from PROCESSING to DELAYED.
    - ORDER_DELAY / SLA_BREACH incident created with ANALYZING status.
    - Advisory RCA generated with HIGH evidence strength recommending EXPEDITE_FULFILMENT.
    - Operator alert issued in audit trail with status AWAITING_OPERATOR_INVESTIGATION.
    - Zero auto-cancellation (order is NOT CANCELLED and NOT FAILED).
    - Resolution is None (no automatic expedition).
    """
    response = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={
            "scenario_key": "SCENARIO_2_SLA_DELAY",
            "customer_name": "Kyle Reese",
            "product_sku": "SKU-CYBER-500",
            "order_amount": 189.99,
            "auto_resolve": False
        }
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True

    data = payload["data"]
    order = data["order"]
    incident = data["incident"]
    rca = data["rca"]
    operator_alert = data.get("operator_alert")

    # 1. State machine transition: Order is marked DELAYED (not FAILED, CANCELLED, or COMPLETED)
    assert order["order_status"] == "DELAYED"
    assert order["order_status"] != "CANCELLED"
    assert order["order_status"] != "FAILED"
    assert order["current_stage"] == "FULFILMENT"
    assert order["inventory_status"] == "RESERVED"
    assert order["payment_status"] == "CAPTURED"

    # 2. Incident created with correct categorization and lifecycle
    assert incident is not None
    assert incident["failure_category"] == "ORDER_DELAY"
    assert incident["failure_type"] == "SLA_BREACH"
    assert incident["incident_status"] == "ANALYZING"
    assert incident["stage"] == "FULFILMENT"
    assert incident["service_name"] == "fulfilment_service"
    assert incident["severity"] == "MEDIUM"

    # 3. Evidence-grounded Advisory RCA
    assert rca is not None
    assert rca["failure_category"] == "ORDER_DELAY"
    assert rca["affected_service"] == "fulfilment_service"
    assert rca["recommended_action"] == "EXPEDITE_FULFILMENT"
    assert rca["risk_level"] == "LOW"
    assert rca["evidence_strength"] in ["HIGH", "MEDIUM", "LOW"]
    assert rca["corroborating_signals_count"] >= 1
    assert any("5000" in ev or "FULFILMENT" in ev for ev in rca["observed_evidence"])

    # 4. Operator Alert Data in response payload
    assert operator_alert is not None
    assert operator_alert["stage"] == "FULFILMENT"
    assert operator_alert["elapsed_duration_ms"] == 10000
    assert operator_alert["sla_threshold_ms"] == 5000
    assert operator_alert["breach_ms"] == 5000
    assert operator_alert["alert_status"] == "AWAITING_OPERATOR_INVESTIGATION"

    # 5. Strict constraint: No automatic resolution in Scenario 2 trigger
    assert data["resolution"] is None

    # 6. Check Audit Trail logs for OPERATOR_ALERT_ISSUED
    audit_resp = client.get(f"/api/v1/audit?order_id={order['order_id']}")
    assert audit_resp.status_code == 200
    logs = audit_resp.json()["data"]
    event_types = [l["event_type"] for l in logs]
    assert "INCIDENT_DETECTED" in event_types
    assert "OPERATOR_ALERT_ISSUED" in event_types
    assert "RCA_COMPLETED" in event_types

    alert_log = next(l for l in logs if l["event_type"] == "OPERATOR_ALERT_ISSUED")
    meta = json.loads(alert_log["metadata_json"]) if alert_log.get("metadata_json") else {}
    assert meta["elapsed_duration_ms"] == 10000
    assert meta["sla_threshold_ms"] == 5000
    assert meta["breach_ms"] == 5000
    assert meta["alert_status"] == "AWAITING_OPERATOR_INVESTIGATION"


def test_scenario_2_does_not_auto_expedite(client: TestClient):
    """Verifies that even if auto_resolve=True is submitted to trigger-scenario for Scenario 2,
    no automatic resolution is dispatched. The order strictly remains DELAYED and the
    incident strictly remains ANALYZING awaiting explicit manual operator action.
    """
    resp = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={"scenario_key": "SCENARIO_2_SLA_DELAY", "auto_resolve": True}
    )
    assert resp.status_code == 200
    data = resp.json()["data"]

    # Must NOT have auto-resolved
    assert data["resolution"] is None
    assert data["order"]["order_status"] == "DELAYED"
    assert data["incident"]["incident_status"] == "ANALYZING"

    # Verify database state confirms order is still DELAYED
    order_resp = client.get(f"/api/v1/orders/{data['order']['order_id']}")
    assert order_resp.status_code == 200
    assert order_resp.json()["data"]["order_status"] == "DELAYED"


def test_sla_policy_engine_authorizations_and_rejections():
    """Verifies that the policy engine strictly authorizes non-destructive expedite actions
    and rejects destructive actions (cancellation, warehouse reassignment, blind retry).
    """
    mock_incident = Incident(
        incident_id="INC-MOCK-DELAY",
        order_id="ORD-MOCK",
        stage="FULFILMENT",
        service_name="fulfilment_service",
        failure_category="ORDER_DELAY",
        failure_type="SLA_BREACH",
        retry_count=0,
        max_retries=1
    )

    # 1. Authorized action: EXPEDITE_FULFILMENT
    auth1, reason1, backoff1, esc1 = policy_engine.evaluate_action(
        mock_incident, "EXPEDITE_FULFILMENT"
    )
    assert auth1 is True
    assert "expedition authorized" in reason1.lower()
    assert backoff1 == 0

    # 2. Authorized action: EXPEDITE_FULFILMENT_QUEUE
    auth2, reason2, backoff2, esc2 = policy_engine.evaluate_action(
        mock_incident, "EXPEDITE_FULFILMENT_QUEUE"
    )
    assert auth2 is True

    # 3. Prohibited action: CANCEL_ORDER (Strict prohibition)
    auth3, reason3, _, _ = policy_engine.evaluate_action(
        mock_incident, "CANCEL_ORDER"
    )
    assert auth3 is False
    assert "prohibited" in reason3.lower()

    # 4. Prohibited action: AUTOMATIC_CANCELLATION
    auth4, reason4, _, _ = policy_engine.evaluate_action(
        mock_incident, "AUTOMATIC_CANCELLATION"
    )
    assert auth4 is False
    assert "prohibited" in reason4.lower()

    # 5. Prohibited action: REASSIGN_WAREHOUSE
    auth5, reason5, _, _ = policy_engine.evaluate_action(
        mock_incident, "REASSIGN_WAREHOUSE"
    )
    assert auth5 is False
    assert "prohibited" in reason5.lower()

    # 6. Prohibited action: Blind RETRY_WITH_BACKOFF
    auth6, reason6, _, _ = policy_engine.evaluate_action(
        mock_incident, "RETRY_WITH_BACKOFF"
    )
    assert auth6 is False
    assert "blind retries prohibited" in reason6.lower()


def test_prohibited_actions_blocked_with_http_400(client: TestClient):
    """Verifies that attempting prohibited actions (CANCEL_ORDER, REASSIGN_WAREHOUSE, RETRY_WITH_BACKOFF)
    via POST /api/v1/resolutions/execute is rejected with HTTP 400 Bad Request and preserves
    the order's DELAYED status.
    """
    init_resp = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={"scenario_key": "SCENARIO_2_SLA_DELAY"}
    )
    assert init_resp.status_code == 200
    init_data = init_resp.json()["data"]
    order_id = init_data["order"]["order_id"]
    incident_id = init_data["incident"]["incident_id"]

    prohibited_actions = ["CANCEL_ORDER", "REASSIGN_WAREHOUSE", "RETRY_WITH_BACKOFF"]
    for action in prohibited_actions:
        res_resp = client.post(
            "/api/v1/resolutions/execute",
            json={
                "incident_id": incident_id,
                "action_type": action,
                "idempotency_key": f"idemp_{order_id}_{action}"
            }
        )
        assert res_resp.status_code == 400
        assert "prohibited" in res_resp.json()["detail"].lower()

    # Confirm order strictly remains DELAYED
    order_resp = client.get(f"/api/v1/orders/{order_id}")
    assert order_resp.status_code == 200
    assert order_resp.json()["data"]["order_status"] == "DELAYED"


def test_sla_delay_recovery_and_downstream_verification(client: TestClient):
    """Verifies operator-authorized manual execution of EXPEDITE_FULFILMENT:
    - Downstream state verification asserts priority queue elevation in domain store.
    - Immediate response returns order_status: PROCESSING.
    - Incident transitions to RESOLVED.
    - Background continuation resumes Stage 6 (Delivery) and Stage 7 (Notification).
    - Order reaches COMPLETED across all 7 stages.
    """
    init_resp = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={"scenario_key": "SCENARIO_2_SLA_DELAY", "auto_resolve": False}
    )
    assert init_resp.status_code == 200
    init_data = init_resp.json()["data"]
    order_id = init_data["order"]["order_id"]
    incident_id = init_data["incident"]["incident_id"]

    idemp_key = f"idemp_{order_id}_EXPEDITE_SUCCESS"

    # Execute authorized expedite action
    res_resp = client.post(
        "/api/v1/resolutions/execute",
        json={
            "incident_id": incident_id,
            "action_type": "EXPEDITE_FULFILMENT",
            "idempotency_key": idemp_key
        }
    )
    assert res_resp.status_code == 200
    res_data = res_resp.json()["data"]

    # Immediate response asserts PROCESSING and verification passed
    assert res_data["action_type"] == "EXPEDITE_FULFILMENT"
    assert res_data["verification_passed"] is True
    assert res_data["execution_status"] == "SUCCEEDED"
    assert res_data["order_status"] == "PROCESSING"
    assert "packaging priority elevated" in res_data["verification_details"].lower()

    # Incident transitioned to RESOLVED
    inc_resp = client.get(f"/api/v1/incidents/{incident_id}")
    assert inc_resp.status_code == 200
    assert inc_resp.json()["data"]["incident"]["incident_status"] == "RESOLVED"

    # Background continuation finished remaining stages to COMPLETED
    order_resp = client.get(f"/api/v1/orders/{order_id}")
    assert order_resp.status_code == 200
    order_data = order_resp.json()["data"]
    assert order_data["order_status"] == "COMPLETED"
    assert order_data["current_stage"] == "NOTIFICATION"
    assert order_data["fulfilment_status"] == "DELIVERED"

    # Check journey stages: all 7 stages succeeded
    journey_resp = client.get(f"/api/v1/orders/{order_id}/journey")
    assert journey_resp.status_code == 200
    stages = journey_resp.json()["data"]["stages"]
    assert len(stages) == 7
    for stage in stages:
        assert stage["status"] == "SUCCESS"


def test_failed_fulfilment_verification_blocks_recovery(client: TestClient, monkeypatch):
    """Verifies that if priority expedite returns HTTP 200 but downstream state verification
    fails (domain record unconfirmed), recovery is NOT declared successful, the incident
    remains open, the order remains DELAYED, and subsequent stages do NOT run.
    """
    init_resp = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={"scenario_key": "SCENARIO_2_SLA_DELAY", "auto_resolve": False}
    )
    assert init_resp.status_code == 200
    init_data = init_resp.json()["data"]
    order_id = init_data["order"]["order_id"]
    incident_id = init_data["incident"]["incident_id"]

    # Mock verify_fulfilment_state to return False despite simulated adapter HTTP 200
    monkeypatch.setattr(
        simulator,
        "verify_fulfilment_state",
        lambda oid: (False, "Verification probe failed: Warehouse queue priority elevation unconfirmed.")
    )

    idemp_key = f"idemp_{order_id}_EXPEDITE_FAIL"
    res_resp = client.post(
        "/api/v1/resolutions/execute",
        json={
            "incident_id": incident_id,
            "action_type": "EXPEDITE_FULFILMENT",
            "idempotency_key": idemp_key
        }
    )
    assert res_resp.status_code == 200
    res_data = res_resp.json()["data"]
    assert res_data["verification_passed"] is False
    assert res_data["execution_status"] == "FAILED"
    assert "Verification probe failed" in res_data["verification_details"]

    # Incident must NOT be RESOLVED
    inc_resp = client.get(f"/api/v1/incidents/{incident_id}")
    assert inc_resp.status_code == 200
    assert inc_resp.json()["data"]["incident"]["incident_status"] != "RESOLVED"

    # Order must remain DELAYED (not COMPLETED or PROCESSING)
    order_resp = client.get(f"/api/v1/orders/{order_id}")
    assert order_resp.status_code == 200
    order_data = order_resp.json()["data"]
    assert order_data["order_status"] == "DELAYED"
    assert order_data["current_stage"] == "FULFILMENT"


def test_sla_delay_idempotency_behavior(client: TestClient):
    """Verifies that resubmitting the expedite action with identical key returns cached 200
    without duplicate execution, and conflicting payload with same key returns HTTP 409 Conflict.
    """
    init_resp = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={"scenario_key": "SCENARIO_2_SLA_DELAY", "auto_resolve": False}
    )
    assert init_resp.status_code == 200
    order_id = init_resp.json()["data"]["order"]["order_id"]
    incident_id = init_resp.json()["data"]["incident"]["incident_id"]

    idemp_key = f"idemp_{order_id}_SLA_IDEMP"

    # Call 1: First dispatch
    first_resp = client.post(
        "/api/v1/resolutions/execute",
        json={"incident_id": incident_id, "action_type": "EXPEDITE_FULFILMENT", "idempotency_key": idemp_key}
    )
    assert first_resp.status_code == 200
    first_action_id = first_resp.json()["data"]["action_id"]

    # Call 2: Identical replay -> returns cached 200
    replay_resp = client.post(
        "/api/v1/resolutions/execute",
        json={"incident_id": incident_id, "action_type": "EXPEDITE_FULFILMENT", "idempotency_key": idemp_key}
    )
    assert replay_resp.status_code == 200
    assert replay_resp.json()["data"]["action_id"] == first_action_id

    # Call 3: Conflicting action with same key -> returns HTTP 409 Conflict
    conflict_resp = client.post(
        "/api/v1/resolutions/execute",
        json={"incident_id": incident_id, "action_type": "CANCEL_ORDER", "idempotency_key": idemp_key}
    )
    assert conflict_resp.status_code == 409
    assert "Idempotency collision" in conflict_resp.json()["detail"]


def test_ui_dashboard_endpoint(client: TestClient):
    """Verifies that the operator monitoring UI dashboard is accessible at /ui
    and serves the HTML view with all required Milestone 2 SLA delay elements.
    """
    resp = client.get("/ui")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    text = resp.text
    assert "OrderFlow Sentinel" in text
    assert "DELAYED" in text
    assert "FULFILMENT" in text
    assert "5,000" in text
    assert "10,000" in text
    assert "OPERATOR ALERT" in text
    assert "AWAITING OPERATOR INVESTIGATION" in text
    assert "EXPEDITE_FULFILMENT" in text
    assert "CANCEL_ORDER" in text
