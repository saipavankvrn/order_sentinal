import pytest
from fastapi.testclient import TestClient
from backend.app.models.order import Incident, Order
from backend.app.db.session import SessionLocal
from backend.app.services.simulator import simulator


def test_scenario_0_clean_order_journey_success(client: TestClient):
    """Verifies that a clean order journey executes through all 7 stages to COMPLETED."""
    response = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={
            "scenario_key": "SCENARIO_0_CLEAN_RUN",
            "customer_name": "John Connor",
            "product_sku": "SKU-CYBER-500",
            "order_amount": 250.00
        }
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True

    data = payload["data"]
    order = data["order"]
    assert order["order_status"] == "COMPLETED"
    assert order["current_stage"] == "NOTIFICATION"
    assert order["payment_status"] == "CAPTURED"
    assert order["inventory_status"] == "RESERVED"
    assert order["fulfilment_status"] == "DELIVERED"
    assert data["incident"] is None

    # Check journey stages
    journey_resp = client.get(f"/api/v1/orders/{order['order_id']}/journey")
    assert journey_resp.status_code == 200
    journey_data = journey_resp.json()["data"]
    assert len(journey_data["stages"]) == 7
    for stage in journey_data["stages"]:
        assert stage["status"] == "SUCCESS"


def test_scenario_1_http_503_detection_and_advisory_rca(client: TestClient):
    """Verifies that HTTP 503 at inventory triggers incident creation, order remains PROCESSING,
    and an advisory RCA report is generated with deterministic fallback.
    """
    response = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={
            "scenario_key": "SCENARIO_1_HTTP_503_SELF_HEAL",
            "customer_name": "Sarah Connor",
            "product_sku": "SKU-CYBER-500",
            "order_amount": 199.99,
            "auto_resolve": False
        }
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True

    data = payload["data"]
    order = data["order"]
    # Critical: Order remains in PROCESSING pending resolution; NOT terminally FAILED
    assert order["order_status"] == "PROCESSING"
    assert order["current_stage"] == "INVENTORY"
    assert order["inventory_status"] == "PENDING"
    assert order["payment_status"] == "CAPTURED"

    # Incident checks
    incident = data["incident"]
    assert incident is not None
    assert incident["failure_category"] == "API_ERROR"
    assert incident["failure_type"] == "HTTP_503"
    assert incident["incident_status"] == "ANALYZING"
    assert incident["retry_count"] == 0
    assert incident["max_retries"] == 3

    # Advisory RCA checks
    rca = data["rca"]
    assert rca is not None
    assert rca["failure_category"] == "API_ERROR"
    assert rca["affected_service"] == "inventory_service"
    assert rca["recommended_action"] == "RETRY_WITH_BACKOFF"
    assert rca["risk_level"] == "LOW"
    assert rca["evidence_strength"] in ["HIGH", "MEDIUM", "LOW"]
    assert rca["corroborating_signals_count"] >= 1
    assert len(rca["observed_evidence"]) >= 1
    assert len(rca["explanation"]) > 0


def test_scenario_1_idempotent_retry_and_downstream_verification(client: TestClient):
    """Verifies that an authorized retry executes, verifies downstream inventory state,
    resolves the incident, and continues remaining stages to COMPLETED.
    """
    # 1. Trigger Scenario 1 without auto-resolve
    init_resp = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={
            "scenario_key": "SCENARIO_1_HTTP_503_SELF_HEAL",
            "auto_resolve": False
        }
    )
    assert init_resp.status_code == 200
    init_data = init_resp.json()["data"]
    incident_id = init_data["incident"]["incident_id"]
    order_id = init_data["order"]["order_id"]

    idemp_key = f"idemp_{order_id}_INVENTORY_1"

    # 2. Execute resolution action
    res_resp = client.post(
        "/api/v1/resolutions/execute",
        json={
            "incident_id": incident_id,
            "action_type": "RETRY_WITH_BACKOFF",
            "idempotency_key": idemp_key
        }
    )
    assert res_resp.status_code == 200
    res_data = res_resp.json()["data"]
    assert res_data["execution_status"] == "SUCCEEDED"
    assert res_data["attempt_number"] == 1
    assert res_data["verification_passed"] is True
    assert res_data["order_status"] == "PROCESSING"
    assert "Reservation" in res_data["verification_details"]

    # 3. Verify order progression: all 7 stages completed!
    order_resp = client.get(f"/api/v1/orders/{order_id}")
    assert order_resp.status_code == 200
    order = order_resp.json()["data"]
    assert order["order_status"] == "COMPLETED"
    assert order["inventory_status"] == "RESERVED"
    assert order["fulfilment_status"] == "DELIVERED"

    # 4. Verify incident status is RESOLVED
    inc_resp = client.get(f"/api/v1/incidents/{incident_id}")
    assert inc_resp.status_code == 200
    assert inc_resp.json()["data"]["incident"]["incident_status"] == "RESOLVED"


def test_resolution_idempotency_behavior(client: TestClient):
    """Verifies that re-submitting with identical idempotency key returns cached result (HTTP 200),
    while a conflicting action with same key returns HTTP 409 Conflict.
    """
    init_resp = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={"scenario_key": "SCENARIO_1_HTTP_503_SELF_HEAL", "auto_resolve": False}
    )
    init_data = init_resp.json()["data"]
    incident_id = init_data["incident"]["incident_id"]
    order_id = init_data["order"]["order_id"]

    idemp_key = f"idemp_{order_id}_INVENTORY_1"

    # First execution
    first_resp = client.post(
        "/api/v1/resolutions/execute",
        json={
            "incident_id": incident_id,
            "action_type": "RETRY_WITH_BACKOFF",
            "idempotency_key": idemp_key
        }
    )
    assert first_resp.status_code == 200
    first_action_id = first_resp.json()["data"]["action_id"]

    # Second execution with identical key and action -> must return HTTP 200 with same action_id
    second_resp = client.post(
        "/api/v1/resolutions/execute",
        json={
            "incident_id": incident_id,
            "action_type": "RETRY_WITH_BACKOFF",
            "idempotency_key": idemp_key
        }
    )
    assert second_resp.status_code == 200
    assert second_resp.json()["data"]["action_id"] == first_action_id

    # Third execution with same key but conflicting action -> must return HTTP 409 Conflict
    conflict_resp = client.post(
        "/api/v1/resolutions/execute",
        json={
            "incident_id": incident_id,
            "action_type": "CANCEL_ORDER",
            "idempotency_key": idemp_key
        }
    )
    assert conflict_resp.status_code == 409
    assert "Idempotency collision" in conflict_resp.json()["detail"]


def test_retry_exhaustion_escalates_incident(client: TestClient):
    """Verifies that after 3 unsuccessful retries, the incident transitions to ESCALATED
    and any further retry attempt is prohibited by policy.
    """
    init_resp = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={"scenario_key": "SCENARIO_1_HTTP_503_SELF_HEAL", "auto_resolve": False}
    )
    init_data = init_resp.json()["data"]
    incident_id = init_data["incident"]["incident_id"]
    order_id = init_data["order"]["order_id"]

    from backend.app.services.resolution_service import resolution_service
    db = SessionLocal()
    try:
        # Simulate 3 persistent failures by forcing downstream failure
        for attempt in range(1, 4):
            idemp_key = f"idemp_{order_id}_INVENTORY_ATTEMPT_{attempt}"
            action = resolution_service.execute_resolution(
                db=db,
                incident_id=incident_id,
                action_type="RETRY_WITH_BACKOFF",
                idempotency_key=idemp_key,
                force_fail_downstream=True
            )
            assert action.attempt_number == attempt
            assert action.verification_passed is False
            assert action.execution_status == "FAILED"

        # Check incident after 3 attempts -> must be ESCALATED
        inc = db.query(Incident).filter_by(incident_id=incident_id).first()
        assert inc.retry_count == 3
        assert inc.incident_status == "ESCALATED"

        # Attempt a 4th retry -> must be rejected by policy engine
        with pytest.raises(Exception) as excinfo:
            resolution_service.execute_resolution(
                db=db,
                incident_id=incident_id,
                action_type="RETRY_WITH_BACKOFF",
                idempotency_key=f"idemp_{order_id}_INVENTORY_ATTEMPT_4"
            )
        assert "exhausted" in str(excinfo.value).lower()
    finally:
        db.close()


def test_privileged_stage_retry_guard():
    """Verifies that the policy engine prohibits blind retries on payment or customer order."""
    from backend.app.policies.policy_engine import policy_engine

    mock_incident = Incident(
        incident_id="INC-MOCK-PAY",
        order_id="ORD-MOCK",
        stage="PAYMENT",
        service_name="payment_service",
        failure_category="API_ERROR",
        failure_type="TIMEOUT",
        retry_count=0,
        max_retries=3
    )
    authorized, reason, backoff, escalate = policy_engine.evaluate_action(
        mock_incident, "RETRY_WITH_BACKOFF"
    )
    assert authorized is False
    assert "blind retry prohibited" in reason.lower()
    assert escalate is True


def test_audit_trail_logging(client: TestClient):
    """Verifies that application-level append-only audit trail captures all milestone lifecycle events."""
    auto_resp = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={
            "scenario_key": "SCENARIO_1_HTTP_503_SELF_HEAL",
            "auto_resolve": True
        }
    )
    assert auto_resp.status_code == 200
    order_id = auto_resp.json()["data"]["order"]["order_id"]

    audit_resp = client.get(f"/api/v1/audit?order_id={order_id}")
    assert audit_resp.status_code == 200
    logs = audit_resp.json()["data"]

    event_types = [l["event_type"] for l in logs]
    assert "ORDER_CREATED" in event_types
    assert "INCIDENT_DETECTED" in event_types
    assert "RCA_COMPLETED" in event_types
    assert "ACTION_DISPATCHED" in event_types
    assert "VERIFICATION_PASSED" in event_types
    assert "INCIDENT_RESOLVED" in event_types
    assert "ORDER_COMPLETED" in event_types


def test_failed_downstream_verification_blocks_recovery(client: TestClient, monkeypatch):
    """Verifies that if inventory retry returns HTTP 200 but downstream state verification
    fails (e.g. domain record missing/unconfirmed), recovery is NOT declared successful,
    the incident remains open, and the order is NOT completed.
    """
    init_resp = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={"scenario_key": "SCENARIO_1_HTTP_503_SELF_HEAL", "auto_resolve": False}
    )
    assert init_resp.status_code == 200
    init_data = init_resp.json()["data"]
    order_id = init_data["order"]["order_id"]
    incident_id = init_data["incident"]["incident_id"]

    # Mock verify_inventory_state to return False despite simulated adapter HTTP 200
    monkeypatch.setattr(
        simulator,
        "verify_inventory_state",
        lambda oid: (False, "Verification probe failed: No confirmed reservation found in domain store.")
    )

    idemp_key = f"idemp_{order_id}_VERIF_FAIL"
    res_resp = client.post(
        "/api/v1/resolutions/execute",
        json={
            "incident_id": incident_id,
            "action_type": "RETRY_WITH_BACKOFF",
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
    inc_data = inc_resp.json()["data"]["incident"]
    assert inc_data["incident_status"] != "RESOLVED"

    # Order must NOT be COMPLETED and inventory must remain PENDING
    order_resp = client.get(f"/api/v1/orders/{order_id}")
    assert order_resp.status_code == 200
    order_data = order_resp.json()["data"]
    assert order_data["order_status"] == "PROCESSING"
    assert order_data["inventory_status"] == "PENDING"


def test_retry_exhaustion_via_api_escalates(client: TestClient, monkeypatch):
    """Verifies that executing retries 1, 2, and 3 through the REST endpoint with downstream
    failures transitions the incident to ESCALATED, and attempt 4 is rejected with HTTP 400.
    """
    init_resp = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={"scenario_key": "SCENARIO_1_HTTP_503_SELF_HEAL", "auto_resolve": False}
    )
    assert init_resp.status_code == 200
    init_data = init_resp.json()["data"]
    order_id = init_data["order"]["order_id"]
    incident_id = init_data["incident"]["incident_id"]

    # Force simulated adapter to return persistent 503 on retry
    monkeypatch.setattr(
        simulator,
        "reserve_inventory",
        lambda order_id, sku, is_retry=False, force_fail=False: (
            503, 350, "FAILED", "HTTP_503_SERVICE_UNAVAILABLE", "Downstream replica outage"
        )
    )

    # Retry 1
    r1 = client.post(
        "/api/v1/resolutions/execute",
        json={"incident_id": incident_id, "action_type": "RETRY_WITH_BACKOFF", "idempotency_key": f"idemp_{order_id}_API_R1"}
    )
    assert r1.status_code == 200
    assert r1.json()["data"]["attempt_number"] == 1
    assert r1.json()["data"]["execution_status"] == "FAILED"

    # Check incident after Retry 1
    inc1 = client.get(f"/api/v1/incidents/{incident_id}").json()["data"]["incident"]
    assert inc1["retry_count"] == 1
    assert inc1["incident_status"] == "RESOLVING"

    # Retry 2
    r2 = client.post(
        "/api/v1/resolutions/execute",
        json={"incident_id": incident_id, "action_type": "RETRY_WITH_BACKOFF", "idempotency_key": f"idemp_{order_id}_API_R2"}
    )
    assert r2.status_code == 200
    assert r2.json()["data"]["attempt_number"] == 2
    assert r2.json()["data"]["execution_status"] == "FAILED"

    # Check incident after Retry 2
    inc2 = client.get(f"/api/v1/incidents/{incident_id}").json()["data"]["incident"]
    assert inc2["retry_count"] == 2
    assert inc2["incident_status"] == "RESOLVING"

    # Retry 3
    r3 = client.post(
        "/api/v1/resolutions/execute",
        json={"incident_id": incident_id, "action_type": "RETRY_WITH_BACKOFF", "idempotency_key": f"idemp_{order_id}_API_R3"}
    )
    assert r3.status_code == 200
    assert r3.json()["data"]["attempt_number"] == 3
    assert r3.json()["data"]["execution_status"] == "FAILED"

    # Check incident after Retry 3 -> Must be ESCALATED
    inc3 = client.get(f"/api/v1/incidents/{incident_id}").json()["data"]["incident"]
    assert inc3["retry_count"] == 3
    assert inc3["incident_status"] == "ESCALATED"

    # Attempt 4: Must be rejected with HTTP 400 Bad Request by policy
    r4 = client.post(
        "/api/v1/resolutions/execute",
        json={"incident_id": incident_id, "action_type": "RETRY_WITH_BACKOFF", "idempotency_key": f"idemp_{order_id}_API_R4"}
    )
    assert r4.status_code == 400
    assert "exhausted" in r4.json()["detail"].lower()

    # Verify no 4th retry executed
    inc4 = client.get(f"/api/v1/incidents/{incident_id}").json()["data"]["incident"]
    assert inc4["retry_count"] == 3
    assert inc4["incident_status"] == "ESCALATED"


def test_resolution_execute_returns_processing_order_status(client: TestClient):
    """Verifies that POST /api/v1/resolutions/execute returns order_status: PROCESSING
    in the immediate response, transitions the incident to RESOLVED, executes remaining stages
    via background continuation, and the order eventually reaches COMPLETED across all 7 stages.
    """
    init_resp = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={"scenario_key": "SCENARIO_1_HTTP_503_SELF_HEAL", "auto_resolve": False}
    )
    assert init_resp.status_code == 200
    init_data = init_resp.json()["data"]
    order_id = init_data["order"]["order_id"]
    incident_id = init_data["incident"]["incident_id"]

    # Execute recovery retry
    idemp_key = f"idemp_{order_id}_PROC_STATUS_CHECK"
    res_resp = client.post(
        "/api/v1/resolutions/execute",
        json={
            "incident_id": incident_id,
            "action_type": "RETRY_WITH_BACKOFF",
            "idempotency_key": idemp_key
        }
    )
    assert res_resp.status_code == 200
    res_data = res_resp.json()["data"]

    # 1. Immediate response contract verification: order_status MUST be PROCESSING
    assert res_data["order_status"] == "PROCESSING"
    assert res_data["verification_passed"] is True
    assert res_data["execution_status"] == "SUCCEEDED"

    # 2. Incident is RESOLVED
    inc_resp = client.get(f"/api/v1/incidents/{incident_id}")
    assert inc_resp.status_code == 200
    assert inc_resp.json()["data"]["incident"]["incident_status"] == "RESOLVED"

    # 3. Order progression: background task executed remaining stages to COMPLETED
    order_resp = client.get(f"/api/v1/orders/{order_id}")
    assert order_resp.status_code == 200
    order_data = order_resp.json()["data"]
    assert order_data["order_status"] == "COMPLETED"
    assert order_data["current_stage"] == "NOTIFICATION"
    assert order_data["inventory_status"] == "RESERVED"
    assert order_data["fulfilment_status"] == "DELIVERED"

    # 4. Check journey timeline: all 7 stages succeeded
    journey_resp = client.get(f"/api/v1/orders/{order_id}/journey")
    assert journey_resp.status_code == 200
    journey_data = journey_resp.json()["data"]
    assert len(journey_data["stages"]) == 7
    for stage in journey_data["stages"]:
        assert stage["status"] == "SUCCESS"


def test_concurrent_background_continuation_executes_once(client: TestClient):
    """Verifies that multiple concurrent threads attempting to execute journey continuation
    for the same order are safely serialized and atomic: each downstream stage executes strictly once.
    """
    import concurrent.futures
    from backend.app.services.order_service import order_service
    from backend.app.db.session import SessionLocal

    init_resp = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={"scenario_key": "SCENARIO_1_HTTP_503_SELF_HEAL", "auto_resolve": False}
    )
    assert init_resp.status_code == 200
    order_id = init_resp.json()["data"]["order"]["order_id"]
    incident_id = init_resp.json()["data"]["incident"]["incident_id"]

    # Mark inventory as recovered directly to simulate post-resolution milestone
    db = SessionLocal()
    try:
        order = db.query(Order).filter_by(order_id=order_id).first()
        order.inventory_status = "RESERVED"
        order.current_stage = "INVENTORY"
        order.order_status = "PROCESSING"
        db.commit()
    finally:
        db.close()

    # Launch 5 concurrent threads attempting to run remaining stages
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(order_service.resume_remaining_stages_background, order_id)
            for _ in range(5)
        ]
        concurrent.futures.wait(futures)

    # Verify order state in database
    db = SessionLocal()
    try:
        updated_order = db.query(Order).filter_by(order_id=order_id).first()
        assert updated_order.order_status == "COMPLETED"
        assert updated_order.current_stage == "NOTIFICATION"

        # Check telemetry event counts: each stage must execute STRICTLY ONCE
        fulfilment_events = [e for e in updated_order.events if e.stage == "FULFILMENT"]
        delivery_events = [e for e in updated_order.events if e.stage == "DELIVERY"]
        notification_events = [e for e in updated_order.events if e.stage == "NOTIFICATION"]

        assert len(fulfilment_events) == 1, f"Expected 1 FULFILMENT event, got {len(fulfilment_events)}"
        assert len(delivery_events) == 1, f"Expected 1 DELIVERY event, got {len(delivery_events)}"
        assert len(notification_events) == 1, f"Expected 1 NOTIFICATION event, got {len(notification_events)}"
    finally:
        db.close()


def test_idempotency_replay_does_not_duplicate_continuation(client: TestClient):
    """Verifies that an identical idempotency replay returns HTTP 200 with cached action
    and does NOT trigger duplicate background execution or create duplicate stage events.
    """
    init_resp = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={"scenario_key": "SCENARIO_1_HTTP_503_SELF_HEAL", "auto_resolve": False}
    )
    assert init_resp.status_code == 200
    order_id = init_resp.json()["data"]["order"]["order_id"]
    incident_id = init_resp.json()["data"]["incident"]["incident_id"]

    idemp_key = f"idemp_{order_id}_REPLAY_SAFETY"

    # Execution 1 (First call)
    first_resp = client.post(
        "/api/v1/resolutions/execute",
        json={
            "incident_id": incident_id,
            "action_type": "RETRY_WITH_BACKOFF",
            "idempotency_key": idemp_key
        }
    )
    assert first_resp.status_code == 200
    first_action_id = first_resp.json()["data"]["action_id"]

    # Execution 2 (Identical replay)
    replay_resp = client.post(
        "/api/v1/resolutions/execute",
        json={
            "incident_id": incident_id,
            "action_type": "RETRY_WITH_BACKOFF",
            "idempotency_key": idemp_key
        }
    )
    assert replay_resp.status_code == 200
    assert replay_resp.json()["data"]["action_id"] == first_action_id

    # Verify stage events on the journey: each stage executed exactly once
    journey_resp = client.get(f"/api/v1/orders/{order_id}/journey")
    assert journey_resp.status_code == 200
    raw_events = journey_resp.json()["data"]["raw_events"]

    fulfilment_events = [e for e in raw_events if e["stage"] == "FULFILMENT"]
    delivery_events = [e for e in raw_events if e["stage"] == "DELIVERY"]
    notification_events = [e for e in raw_events if e["stage"] == "NOTIFICATION"]

    assert len(fulfilment_events) == 1
    assert len(delivery_events) == 1
    assert len(notification_events) == 1


