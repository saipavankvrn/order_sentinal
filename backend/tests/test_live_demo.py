import uuid
import pytest
from fastapi.testclient import TestClient


def test_live_demo_scenario_0_clean_order(client: TestClient):
    """Verifies fresh live demo order creation with Scenario 0 Clean Run."""
    custom_id = f"ORD-LIVE-{uuid.uuid4().hex[:6].upper()}"
    session_id = f"SESSION-{uuid.uuid4().hex[:6].upper()}"

    resp = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={
            "scenario_key": "SCENARIO_0_CLEAN_RUN",
            "order_id": custom_id,
            "customer_name": "Kyle Reese",
            "is_demo_order": True,
            "demo_session_id": session_id
        }
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    order = data["order"]

    assert order["order_id"] == custom_id
    assert order["is_demo_order"] is True
    assert order["demo_session_id"] == session_id
    assert order["order_status"] == "COMPLETED"
    assert data["incident"] is None


def test_live_demo_scenario_1_http_503_self_heal(client: TestClient):
    """Verifies live demo order creation with Scenario 1 HTTP 503 Self-Healing."""
    custom_id = f"ORD-LIVE-{uuid.uuid4().hex[:6].upper()}"
    session_id = f"SESSION-{uuid.uuid4().hex[:6].upper()}"

    resp = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={
            "scenario_key": "SCENARIO_1_HTTP_503_SELF_HEAL",
            "order_id": custom_id,
            "customer_name": "Sarah Connor",
            "auto_resolve": True,
            "is_demo_order": True,
            "demo_session_id": session_id
        }
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    order = data["order"]
    incident = data["incident"]
    rca = data["rca"]
    resolution = data["resolution"]

    assert order["order_id"] == custom_id
    assert order["is_demo_order"] is True
    assert order["demo_session_id"] == session_id
    assert incident is not None
    assert incident["failure_category"] == "API_ERROR"
    assert rca["recommended_action"] == "RETRY_WITH_BACKOFF"
    assert resolution["verification_passed"] is True
    assert resolution["execution_status"] == "SUCCEEDED"


def test_live_demo_scenario_2_sla_delay(client: TestClient):
    """Verifies live demo order creation with Scenario 2 SLA Delay without auto-expedition."""
    custom_id = f"ORD-LIVE-{uuid.uuid4().hex[:6].upper()}"
    session_id = f"SESSION-{uuid.uuid4().hex[:6].upper()}"

    resp = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={
            "scenario_key": "SCENARIO_2_SLA_DELAY",
            "order_id": custom_id,
            "customer_name": "John Connor",
            "is_demo_order": True,
            "demo_session_id": session_id
        }
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    order = data["order"]
    incident = data["incident"]
    alert = data["operator_alert"]

    assert order["order_id"] == custom_id
    assert order["order_status"] == "DELAYED"
    assert order["is_demo_order"] is True
    assert incident["failure_category"] == "ORDER_DELAY"
    assert incident["failure_type"] == "SLA_BREACH"
    assert alert is not None
    assert alert["stage"] == "FULFILMENT"
    assert alert["elapsed_duration_ms"] == 10000
    assert alert["alert_status"] == "AWAITING_OPERATOR_INVESTIGATION"


def test_live_demo_scenario_3_hitl_approval(client: TestClient):
    """Verifies live demo order creation with Scenario 3 HTTP 422 and operator approval."""
    custom_id = f"ORD-LIVE-{uuid.uuid4().hex[:6].upper()}"
    session_id = f"SESSION-{uuid.uuid4().hex[:6].upper()}"

    resp = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={
            "scenario_key": "SCENARIO_3_HARD_REJECTION",
            "order_id": custom_id,
            "customer_name": "Miles Dyson",
            "is_demo_order": True,
            "demo_session_id": session_id
        }
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    order = data["order"]
    incident = data["incident"]
    approval = data["approval"]

    assert order["order_id"] == custom_id
    assert order["order_status"] == "PROCESSING"
    assert incident["failure_type"] == "OUT_OF_STOCK"
    assert approval is not None
    assert approval["decision"] == "PENDING"

    # Verify pending approvals filtering by demo_session_id
    app_resp = client.get(f"/api/v1/approvals/pending?demo_session_id={session_id}")
    assert app_resp.status_code == 200
    demo_apps = app_resp.json()["data"]
    assert any(a["approval_id"] == approval["approval_id"] for a in demo_apps)

    # Operator approves substitution
    decide_resp = client.post(
        f"/api/v1/approvals/{approval['approval_id']}/decide",
        json={
            "decision": "APPROVED",
            "operator_id": "OP-DEMO-01",
            "operator_name": "Devin Lead",
            "operator_notes": "Stock verified at East hub",
            "selected_action": "SUBSTITUTE_SKU_AND_REALLOCATE",
            "action_parameters": {
                "substitute_sku": "SKU-CYBER-500-ALT",
                "alternate_hub": "HUB-EAST-02"
            }
        }
    )
    assert decide_resp.status_code == 200
    dec_data = decide_resp.json()["data"]
    assert dec_data["decision"] == "APPROVED"
    assert dec_data["verification_passed"] is True


def test_live_demo_random_mode_deterministic_overrides(client: TestClient):
    """Verifies Random Demo Mode with deterministic test overrides for all 4 outcomes."""
    session_id = f"SESSION-{uuid.uuid4().hex[:6].upper()}"

    # 1. Override: SUCCESS (Normal Clean Run)
    resp1 = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={
            "scenario_key": "RANDOM",
            "random_outcome_override": "SUCCESS",
            "customer_name": "Demo User 1",
            "is_demo_order": True,
            "demo_session_id": session_id
        }
    )
    assert resp1.status_code == 200
    d1 = resp1.json()["data"]
    assert d1["scenario_key"] == "SCENARIO_0_CLEAN_RUN"
    assert d1["selected_outcome"] == "NORMAL_SUCCESS"
    assert d1["order"]["order_status"] == "COMPLETED"

    # 2. Override: HTTP_503 (API Failure)
    resp2 = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={
            "scenario_key": "RANDOM",
            "random_outcome_override": "HTTP_503",
            "customer_name": "Demo User 2",
            "auto_resolve": True,
            "is_demo_order": True,
            "demo_session_id": session_id
        }
    )
    assert resp2.status_code == 200
    d2 = resp2.json()["data"]
    assert d2["scenario_key"] == "SCENARIO_1_HTTP_503_SELF_HEAL"
    assert d2["selected_outcome"] == "HTTP_503_API_FAILURE"
    assert d2["incident"]["failure_category"] == "API_ERROR"

    # 3. Override: SLA_DELAY
    resp3 = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={
            "scenario_key": "RANDOM",
            "random_outcome_override": "SLA_DELAY",
            "customer_name": "Demo User 3",
            "is_demo_order": True,
            "demo_session_id": session_id
        }
    )
    assert resp3.status_code == 200
    d3 = resp3.json()["data"]
    assert d3["scenario_key"] == "SCENARIO_2_SLA_DELAY"
    assert d3["selected_outcome"] == "SLA_DELAY"
    assert d3["order"]["order_status"] == "DELAYED"

    # 4. Override: OUT_OF_STOCK
    resp4 = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={
            "scenario_key": "RANDOM",
            "random_outcome_override": "OUT_OF_STOCK",
            "customer_name": "Demo User 4",
            "is_demo_order": True,
            "demo_session_id": session_id
        }
    )
    assert resp4.status_code == 200
    d4 = resp4.json()["data"]
    assert d4["scenario_key"] == "SCENARIO_3_HARD_REJECTION"
    assert d4["selected_outcome"] == "HTTP_422_OUT_OF_STOCK"
    assert d4["approval"] is not None


def test_live_demo_random_mode_probabilities_and_seed(client: TestClient):
    """Verifies Random Demo Mode with random_seed and checks probability distribution."""
    # Seed 42: roll will deterministically pick an outcome
    resp = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={
            "scenario_key": "RANDOM",
            "random_seed": 42,
            "customer_name": "Seeded Customer"
        }
    )
    assert resp.status_code == 200
    d = resp.json()["data"]
    assert d["selected_outcome"] in ["NORMAL_SUCCESS", "HTTP_503_API_FAILURE", "SLA_DELAY", "HTTP_422_OUT_OF_STOCK"]
    assert d["demo_probabilities"] == {
        "success": 0.50,
        "api_failure": 0.25,
        "sla_delay": 0.15,
        "business_rejection": 0.10
    }
    assert d["outcome_reason"] is not None


def test_live_demo_session_reset_purges_only_session_orders(client: TestClient):
    """Verifies that reset_demo_session clears only the target session's orders,
    leaving other demo sessions and historical records untouched.
    """
    session_a = f"SESSION-A-{uuid.uuid4().hex[:6].upper()}"
    session_b = f"SESSION-B-{uuid.uuid4().hex[:6].upper()}"

    # Create 2 orders in session A
    client.post(
        "/api/v1/simulation/trigger-scenario",
        json={"scenario_key": "SCENARIO_0_CLEAN_RUN", "is_demo_order": True, "demo_session_id": session_a}
    )
    client.post(
        "/api/v1/simulation/trigger-scenario",
        json={"scenario_key": "SCENARIO_1_HTTP_503_SELF_HEAL", "is_demo_order": True, "demo_session_id": session_a}
    )

    # Create 1 order in session B
    resp_b = client.post(
        "/api/v1/simulation/trigger-scenario",
        json={"scenario_key": "SCENARIO_0_CLEAN_RUN", "is_demo_order": True, "demo_session_id": session_b}
    )
    order_b_id = resp_b.json()["data"]["order"]["order_id"]

    # Check orders in session A
    orders_a_resp = client.get(f"/api/v1/orders?demo_session_id={session_a}&is_demo=true")
    assert orders_a_resp.status_code == 200
    assert orders_a_resp.json()["data"]["total"] == 2

    # Reset session A
    reset_resp = client.post(
        "/api/v1/simulation/reset-demo-session",
        json={"demo_session_id": session_a}
    )
    assert reset_resp.status_code == 200
    assert reset_resp.json()["data"]["cleared_orders_count"] == 2

    # Verify session A orders are gone
    orders_a_after = client.get(f"/api/v1/orders?demo_session_id={session_a}&is_demo=true")
    assert orders_a_after.json()["data"]["total"] == 0

    # Verify session B order is STILL PRESENT and untouched
    orders_b_after = client.get(f"/api/v1/orders?demo_session_id={session_b}&is_demo=true")
    assert orders_b_after.json()["data"]["total"] == 1
    assert orders_b_after.json()["data"]["items"][0]["order_id"] == order_b_id

