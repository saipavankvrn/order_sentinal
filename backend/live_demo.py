import json
from fastapi.testclient import TestClient
from backend.app.main import app

def run_live_demonstration():
    client = TestClient(app)
    
    print("=" * 80)
    print("ORDERFLOW SENTINEL — LIVE END-TO-END DEMONSTRATION")
    print("=" * 80)

    # 1. Health Check
    print("\n--- 1. GET /api/v1/health ---")
    resp_health = client.get("/api/v1/health")
    print(f"Status: {resp_health.status_code}")
    print(json.dumps(resp_health.json(), indent=2))

    # -------------------------------------------------------------------------
    # SCENARIO 1: HTTP 503 SELF-HEALING
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("SCENARIO 1: HTTP 503 INVENTORY FAILURE & SELF-HEALING")
    print("=" * 80)

    payload_s1 = {
        "scenario_key": "SCENARIO_1_HTTP_503_SELF_HEAL",
        "customer_name": "Sarah Connor",
        "product_sku": "SKU-CYBER-500",
        "order_amount": 199.99,
        "auto_resolve": False
    }
    resp_trigger1 = client.post("/api/v1/simulation/trigger-scenario", json=payload_s1)
    print(f"Trigger Status: {resp_trigger1.status_code}")
    trigger_data1 = resp_trigger1.json()
    order_id1 = trigger_data1["data"]["order"]["order_id"]
    incident_id1 = trigger_data1["data"]["incident"]["incident_id"]
    print(f"Order: {order_id1} | Status: {trigger_data1['data']['order']['order_status']} | Stage: {trigger_data1['data']['order']['current_stage']}")
    print(f"Incident: {incident_id1} | Status: {trigger_data1['data']['incident']['incident_status']} | RCA: {trigger_data1['data']['rca']['recommended_action']}")

    # Execute S1 Resolution
    idemp_s1 = f"idemp_{order_id1}_INVENTORY_1"
    resp_res1 = client.post("/api/v1/resolutions/execute", json={
        "incident_id": incident_id1,
        "action_type": "RETRY_WITH_BACKOFF",
        "idempotency_key": idemp_s1
    })
    print(f"Resolution Status: {resp_res1.status_code} | Action Order Status: {resp_res1.json()['data']['order_status']}")

    # Final S1 State
    resp_order1 = client.get(f"/api/v1/orders/{order_id1}")
    print(f"Post-Continuation Order Status: {resp_order1.json()['data']['order_status']}")

    # -------------------------------------------------------------------------
    # SCENARIO 2: SLA DELAY DETECTION & PRIORITY EXPEDITE
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("SCENARIO 2: FULFILMENT SLA DELAY & PRIORITY EXPEDITE")
    print("=" * 80)

    payload_s2 = {
        "scenario_key": "SCENARIO_2_SLA_DELAY",
        "customer_name": "Kyle Reese",
        "product_sku": "SKU-CYBER-500",
        "order_amount": 189.99,
        "auto_resolve": False
    }
    resp_trigger2 = client.post("/api/v1/simulation/trigger-scenario", json=payload_s2)
    print(f"Trigger Status: {resp_trigger2.status_code}")
    trigger_data2 = resp_trigger2.json()
    print(json.dumps(trigger_data2, indent=2))

    order_id2 = trigger_data2["data"]["order"]["order_id"]
    incident_id2 = trigger_data2["data"]["incident"]["incident_id"]

    # Test Prohibited Action Rejection (Cancellation prohibited on delay)
    print(f"\n--- Policy Prohibits Automatic Cancellation on SLA Delay ---")
    resp_bad = client.post("/api/v1/resolutions/execute", json={
        "incident_id": incident_id2,
        "action_type": "CANCEL_ORDER",
        "idempotency_key": f"idemp_{order_id2}_CANCEL"
    })
    print(f"Status: {resp_bad.status_code} (Expected 400 Bad Request)")
    print(f"Detail: {resp_bad.json()['detail']}")

    # Execute Authorized Expedite Action
    idemp_s2 = f"idemp_{order_id2}_EXPEDITE_1"
    print(f"\n--- POST /api/v1/resolutions/execute (Action: EXPEDITE_FULFILMENT) ---")
    resp_res2 = client.post("/api/v1/resolutions/execute", json={
        "incident_id": incident_id2,
        "action_type": "EXPEDITE_FULFILMENT",
        "idempotency_key": idemp_s2
    })
    print(f"Status: {resp_res2.status_code}")
    print(json.dumps(resp_res2.json(), indent=2))

    # Replay Idempotency Check
    print(f"\n--- Replay Idempotency Check ---")
    resp_replay2 = client.post("/api/v1/resolutions/execute", json={
        "incident_id": incident_id2,
        "action_type": "EXPEDITE_FULFILMENT",
        "idempotency_key": idemp_s2
    })
    print(f"Replay Status: {resp_replay2.status_code} | Action ID Matches: {resp_replay2.json()['data']['action_id'] == resp_res2.json()['data']['action_id']}")

    # Final Order State
    print(f"\n--- GET /api/v1/orders/{order_id2} (Final State) ---")
    resp_order2 = client.get(f"/api/v1/orders/{order_id2}")
    print(f"Order Status: {resp_order2.json()['data']['order_status']} | Stage: {resp_order2.json()['data']['current_stage']}")

    # Journey Timeline
    print(f"\n--- GET /api/v1/orders/{order_id2}/journey ---")
    resp_journey2 = client.get(f"/api/v1/orders/{order_id2}/journey")
    print(f"Stages: {[s['stage_name'] + ': ' + s['status'] for s in resp_journey2.json()['data']['stages']]}")

    # Audit Trail
    print(f"\n--- GET /api/v1/audit?order_id={order_id2} ---")
    resp_audit2 = client.get(f"/api/v1/audit?order_id={order_id2}")
    for log in resp_audit2.json()["data"]:
        print(f"[{log['event_type']}] Actor: {log['actor_type']}:{log['actor_id']} | {log['summary']}")

if __name__ == "__main__":
    run_live_demonstration()
