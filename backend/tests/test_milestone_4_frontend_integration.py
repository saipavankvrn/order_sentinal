import pytest
from fastapi.testclient import TestClient
from backend.app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_milestone_4_ui_serves_spa_with_all_contract_markers(client: TestClient):
    """Verifies that /ui serves the production SPA and contains all contract markers."""
    resp = client.get("/ui")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    text = resp.text

    # App title & structure
    assert "OrderFlow Sentinel" in text
    assert '<div id="root">' in text

    # Milestone 2 markers
    assert "DELAYED" in text
    assert "FULFILMENT" in text
    assert "5,000" in text
    assert "10,000" in text
    assert "OPERATOR ALERT" in text
    assert "AWAITING OPERATOR INVESTIGATION" in text
    assert "EXPEDITE_FULFILMENT" in text
    assert "CANCEL_ORDER" in text

    # Milestone 3 markers
    assert "Human-in-the-Loop Approval Queue" in text
    assert "HIGH RISK" in text
    assert "substituteSkuInput" in text
    assert "alternateHubInput" in text
    assert "Approve Substitution" in text
    assert "Reject Order" in text
    assert "SCENARIO_3_HARD_REJECTION" in text


def test_milestone_4_scenario_0_clean_run_lifecycle(client: TestClient):
    """Verifies Scenario 0 execution through API, confirming 7 stages, COMPLETED status, and audit."""
    resp = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={"scenario_key": "SCENARIO_0_CLEAN_RUN", "customer_name": "Alice Clean"}
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    order_id = data["order"]["order_id"]
    assert data["order"]["order_status"] == "COMPLETED"

    # Verify 7-stage journey
    journey_resp = client.get(f"/api/v1/orders/{order_id}/journey")
    assert journey_resp.status_code == 200
    journey = journey_resp.json()["data"]
    assert len(journey["stages"]) == 7
    for stage in journey["stages"]:
        assert stage["status"] == "SUCCESS"


def test_milestone_4_scenario_1_self_heal_journey(client: TestClient):
    """Verifies Scenario 1 execution, confirming HTTP 503 incident, advisory RCA, and self-heal resolution."""
    resp = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={"scenario_key": "SCENARIO_1_HTTP_503_SELF_HEAL", "customer_name": "Bob SelfHeal", "auto_resolve": True}
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    order_id = data["order"]["order_id"]
    assert data["incident"] is not None
    assert data["resolution"] is not None
    assert data["resolution"]["verification_passed"] is True

    # Verify RCA report exists and has advisory signals
    rca = data.get("rca")
    assert rca is not None
    assert rca["evidence_strength"] in ["HIGH", "MEDIUM", "LOW"]
    assert rca["recommended_action"] == "RETRY_WITH_BACKOFF"


def test_milestone_4_scenario_2_sla_delay_and_alert(client: TestClient):
    """Verifies Scenario 2 delay detection, DELAYED order status, and zero automatic expedition."""
    resp = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={"scenario_key": "SCENARIO_2_SLA_DELAY", "customer_name": "Charlie Delay", "auto_resolve": False}
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    order_id = data["order"]["order_id"]
    assert data["order"]["order_status"] == "DELAYED"
    assert data["incident"]["failure_type"] == "SLA_BREACH"
    assert data["resolution"] is None  # Prohibits auto-expedite


def test_milestone_4_scenario_3_hitl_approval_and_verification(client: TestClient):
    """Verifies Scenario 3 HTTP 422 routing to pending approvals, operator decision submission, and stock verification."""
    # Step 1: Trigger Scenario 3
    init_resp = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={"scenario_key": "SCENARIO_3_HARD_REJECTION", "product_sku": "SKU-CYBER-500"}
    )
    assert init_resp.status_code == 200
    init_data = init_resp.json()["data"]
    approval_id = init_data["approval"]["approval_id"]
    order_id = init_data["order"]["order_id"]

    # Step 2: Confirm pending approval queue has the item
    queue_resp = client.get("/api/v1/approvals/pending")
    assert queue_resp.status_code == 200
    pending_ids = [a["approval_id"] for a in queue_resp.json()["data"]]
    assert approval_id in pending_ids

    # Step 3: Submit approval with substitute SKU & alternate hub
    decision_resp = client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={
            "decision": "APPROVED",
            "operator_id": "OP-JATAYU-01",
            "operator_name": "Devin Lead",
            "operator_notes": "Replenishment confirmed at HUB-EAST-02.",
            "selected_action": "SUBSTITUTE_SKU_AND_REALLOCATE",
            "action_parameters": {
                "substitute_sku": "SKU-CYBER-500-ALT",
                "alternate_hub": "HUB-EAST-02"
            }
        }
    )
    assert decision_resp.status_code == 200
    dec_data = decision_resp.json()["data"]
    assert dec_data["verification_passed"] is True
    assert dec_data["order_status"] == "PROCESSING"

    # Step 4: Audit trail records the operator decision
    audit_resp = client.get(f"/api/v1/audit?order_id={order_id}")
    assert audit_resp.status_code == 200
    events = audit_resp.json()["data"]
    event_types = [e["event_type"] for e in events]
    assert "OPERATOR_APPROVED" in event_types
    assert "VERIFICATION_PASSED" in event_types
    assert "INCIDENT_RESOLVED" in event_types


def test_incidents_endpoint_order_id_filtering(client: TestClient):
    """Verifies DEF-01 fix: GET /api/v1/incidents?order_id=... filters strictly by order_id."""
    # Order A with an incident
    resp_a = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={"scenario_key": "SCENARIO_1_HTTP_503_SELF_HEAL", "customer_name": "Order A Filter", "auto_resolve": False}
    )
    assert resp_a.status_code == 200
    order_a_id = resp_a.json()["data"]["order"]["order_id"]

    # Order B with clean run (no incident)
    resp_b = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={"scenario_key": "SCENARIO_0_CLEAN_RUN", "customer_name": "Order B Clean"}
    )
    assert resp_b.status_code == 200
    order_b_id = resp_b.json()["data"]["order"]["order_id"]

    # Query incidents for Order A -> should return Order A's incident
    inc_a_resp = client.get(f"/api/v1/incidents?order_id={order_a_id}")
    assert inc_a_resp.status_code == 200
    inc_a_list = inc_a_resp.json()["data"]
    assert len(inc_a_list) >= 1
    for inc in inc_a_list:
        assert inc["order_id"] == order_a_id

    # Query incidents for Order B -> should return empty list []
    inc_b_resp = client.get(f"/api/v1/incidents?order_id={order_b_id}")
    assert inc_b_resp.status_code == 200
    inc_b_list = inc_b_resp.json()["data"]
    assert len(inc_b_list) == 0


def test_order_journey_stage_http_status_and_raw_events(client: TestClient):
    """Verifies DEF-03 & DEF-04 fixes: Journey stages include http_status and raw_events array."""
    resp = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={"scenario_key": "SCENARIO_0_CLEAN_RUN", "customer_name": "Journey HTTP Test"}
    )
    assert resp.status_code == 200
    order_id = resp.json()["data"]["order"]["order_id"]

    journey_resp = client.get(f"/api/v1/orders/{order_id}/journey")
    assert journey_resp.status_code == 200
    data = journey_resp.json()["data"]

    # Verify stages have http_status
    assert "stages" in data
    assert len(data["stages"]) == 7
    for stage in data["stages"]:
        assert stage["http_status"] == 200

    # Verify raw_events list exists
    assert "raw_events" in data
    assert len(data["raw_events"]) >= 7


def test_orders_pagination_server_side_offset_and_skip(client: TestClient):
    """Verifies server-side pagination: skip changes, offset is applied, and distinct pages return distinct orders."""
    # Seed at least 8 orders for pagination verification
    created_order_ids = []
    for i in range(8):
        resp = client.post(
            "/api/v1/simulation/trigger-scenario",
            json={"scenario_key": "SCENARIO_0_CLEAN_RUN", "customer_name": f"Pagination Customer {i}"}
        )
        assert resp.status_code == 200
        created_order_ids.append(resp.json()["data"]["order"]["order_id"])

    # Fetch Page 1 with limit=3
    resp_p1 = client.get("/api/v1/orders?page=1&limit=3")
    assert resp_p1.status_code == 200
    p1_data = resp_p1.json()["data"]
    assert p1_data["page"] == 1
    assert p1_data["limit"] == 3
    assert p1_data["total"] >= 8
    assert len(p1_data["items"]) == 3
    p1_ids = [item["order_id"] for item in p1_data["items"]]

    # Fetch Page 2 with skip=3, limit=3
    resp_p2 = client.get("/api/v1/orders?page=2&skip=3&limit=3")
    assert resp_p2.status_code == 200
    p2_data = resp_p2.json()["data"]
    assert p2_data["page"] == 2
    assert p2_data["skip"] == 3
    assert p2_data["limit"] == 3
    assert len(p2_data["items"]) == 3
    p2_ids = [item["order_id"] for item in p2_data["items"]]

    # Assert Page 1 and Page 2 have zero ID overlap
    assert set(p1_ids).isdisjoint(set(p2_ids))

    # Fetch with explicit skip=5, limit=3 (navigating across page boundaries)
    resp_skip = client.get("/api/v1/orders?skip=5&limit=3")
    assert resp_skip.status_code == 200
    skip_data = resp_skip.json()["data"]
    assert skip_data["skip"] == 5
    assert skip_data["page"] == 2
    assert len(skip_data["items"]) == 3

