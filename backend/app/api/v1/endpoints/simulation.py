import json
import random
import uuid
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from backend.app.db.session import get_db
from backend.app.models.order import (
    Order,
    OrderEvent,
    Incident,
    RCAReport,
    ResolutionAction,
    OperatorApproval,
    AuditLog
)
from backend.app.schemas.order import OrderCreate, OrderResponse, OrderEventResponse
from backend.app.schemas.incident import IncidentResponse, RCAReportResponse
from backend.app.schemas.resolution import ResolutionActionResponse
from backend.app.schemas.approval import ApprovalResponse
from backend.app.schemas.simulation import (
    SimulationTriggerRequest,
    SimulationScenarioResponse,
    DemoSessionResetRequest,
    DemoSessionResetResponse
)
from backend.app.schemas.common import ApiResponse
from backend.app.services.order_service import order_service
from backend.app.services.resolution_service import resolution_service
from backend.app.services.audit_service import audit_service
from backend.app.core.logging import logger

router = APIRouter()

# Default demonstration outcome probabilities for Random Demo Mode
DEMO_PROBABILITIES: Dict[str, float] = {
    "success": 0.50,
    "api_failure": 0.25,
    "sla_delay": 0.15,
    "business_rejection": 0.10
}


@router.post(
    "/simulation/trigger-scenario",
    response_model=ApiResponse[SimulationScenarioResponse],
    summary="Trigger Demonstration Scenario",
    description="Executes a live test order through Scenario 0, 1, 2, 3 or Random Demo Mode."
)
def trigger_scenario(
    request: SimulationTriggerRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    raw_scenario = request.scenario_key.strip().upper()
    scenario_map = {
        "SCENARIO_0_CLEAN_RUN": "SCENARIO_0_CLEAN_RUN",
        "SCENARIO_0": "SCENARIO_0_CLEAN_RUN",
        "CLEAN_RUN": "SCENARIO_0_CLEAN_RUN",
        "NORMAL": "SCENARIO_0_CLEAN_RUN",
        "SCENARIO_1_HTTP_503_SELF_HEAL": "SCENARIO_1_HTTP_503_SELF_HEAL",
        "SCENARIO_1": "SCENARIO_1_HTTP_503_SELF_HEAL",
        "HTTP_503": "SCENARIO_1_HTTP_503_SELF_HEAL",
        "SCENARIO_2_SLA_DELAY": "SCENARIO_2_SLA_DELAY",
        "SCENARIO_2": "SCENARIO_2_SLA_DELAY",
        "SLA_DELAY": "SCENARIO_2_SLA_DELAY",
        "SCENARIO_3_HARD_REJECTION": "SCENARIO_3_HARD_REJECTION",
        "SCENARIO_3": "SCENARIO_3_HARD_REJECTION",
        "HARD_REJECTION": "SCENARIO_3_HARD_REJECTION",
        "OUT_OF_STOCK": "SCENARIO_3_HARD_REJECTION",
        "RANDOM": "RANDOM",
        "SCENARIO_RANDOM": "RANDOM"
    }

    if raw_scenario not in scenario_map:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported scenario '{request.scenario_key}'. Supported: "
                "SCENARIO_0_CLEAN_RUN, SCENARIO_1_HTTP_503_SELF_HEAL, "
                "SCENARIO_2_SLA_DELAY, SCENARIO_3_HARD_REJECTION, RANDOM"
            )
        )

    requested_mode = scenario_map[raw_scenario]
    selected_outcome = None
    outcome_reason = None

    # Resolve Random Demo Mode
    if requested_mode == "RANDOM":
        if request.random_outcome_override:
            override = request.random_outcome_override.strip().upper()
            if override in ["SUCCESS", "NORMAL", "SCENARIO_0_CLEAN_RUN"]:
                scenario = "SCENARIO_0_CLEAN_RUN"
                selected_outcome = "NORMAL_SUCCESS"
                outcome_reason = "Deterministic test override: Normal Baseline Journey (50% probability bracket)"
            elif override in ["503", "HTTP_503", "API_FAILURE", "SCENARIO_1_HTTP_503_SELF_HEAL"]:
                scenario = "SCENARIO_1_HTTP_503_SELF_HEAL"
                selected_outcome = "HTTP_503_API_FAILURE"
                outcome_reason = "Deterministic test override: HTTP 503 Self-Healing (25% probability bracket)"
            elif override in ["SLA", "SLA_DELAY", "DELAY", "SCENARIO_2_SLA_DELAY"]:
                scenario = "SCENARIO_2_SLA_DELAY"
                selected_outcome = "SLA_DELAY"
                outcome_reason = "Deterministic test override: Warehouse SLA Delay (15% probability bracket)"
            elif override in ["422", "HTTP_422", "REJECTION", "OUT_OF_STOCK", "SCENARIO_3_HARD_REJECTION"]:
                scenario = "SCENARIO_3_HARD_REJECTION"
                selected_outcome = "HTTP_422_OUT_OF_STOCK"
                outcome_reason = "Deterministic test override: Out-of-Stock Rejection (10% probability bracket)"
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid random_outcome_override '{request.random_outcome_override}'. Use SUCCESS, HTTP_503, SLA_DELAY, or OUT_OF_STOCK."
                )
        else:
            rng = random.Random(request.random_seed) if request.random_seed is not None else random.Random()
            roll = rng.random()
            if roll < 0.50:
                scenario = "SCENARIO_0_CLEAN_RUN"
                selected_outcome = "NORMAL_SUCCESS"
                outcome_reason = f"Random outcome selected [roll: {roll:.2f} < 0.50]: Normal Success (50% probability)"
            elif roll < 0.75:
                scenario = "SCENARIO_1_HTTP_503_SELF_HEAL"
                selected_outcome = "HTTP_503_API_FAILURE"
                outcome_reason = f"Random outcome selected [roll: {roll:.2f} in 0.50..0.75]: HTTP 503 API Failure (25% probability)"
            elif roll < 0.90:
                scenario = "SCENARIO_2_SLA_DELAY"
                selected_outcome = "SLA_DELAY"
                outcome_reason = f"Random outcome selected [roll: {roll:.2f} in 0.75..0.90]: Warehouse SLA Delay (15% probability)"
            else:
                scenario = "SCENARIO_3_HARD_REJECTION"
                selected_outcome = "HTTP_422_OUT_OF_STOCK"
                outcome_reason = f"Random outcome selected [roll: {roll:.2f} >= 0.90]: HTTP 422 Out-of-Stock Rejection (10% probability)"
    else:
        scenario = requested_mode
        labels = {
            "SCENARIO_0_CLEAN_RUN": "NORMAL_SUCCESS",
            "SCENARIO_1_HTTP_503_SELF_HEAL": "HTTP_503_API_FAILURE",
            "SCENARIO_2_SLA_DELAY": "SLA_DELAY",
            "SCENARIO_3_HARD_REJECTION": "HTTP_422_OUT_OF_STOCK"
        }
        selected_outcome = labels.get(scenario, scenario)
        outcome_reason = f"Operator manually selected scenario: {scenario}"

    # Step 1: Create fresh database order record
    order_in = OrderCreate(
        customer_name=request.customer_name or "Sarah Connor",
        customer_email=request.customer_email or "sarah.connor@example.com",
        product_sku=request.product_sku or "SKU-CYBER-500",
        product_name=request.product_name or "High-Performance Fiber Gateway",
        order_amount=request.order_amount or 199.99,
        currency="USD",
        is_demo_order=request.is_demo_order if request.is_demo_order is not None else True,
        demo_session_id=request.demo_session_id
    )
    order = order_service.create_order(
        db=db,
        order_in=order_in,
        custom_order_id=request.order_id,
        is_demo_order=order_in.is_demo_order,
        demo_session_id=order_in.demo_session_id
    )

    incident = None
    rca_resp = None
    resolution_resp = None
    approval_resp = None
    operator_alert = None

    if scenario == "SCENARIO_0_CLEAN_RUN":
        order, _ = order_service.execute_journey(db, order, inject_inventory_503=False)
        msg = f"Clean order journey executed successfully through all 7 stages. Final Status: COMPLETED. Order: {order.order_id}"

    elif scenario == "SCENARIO_1_HTTP_503_SELF_HEAL":
        order, incident = order_service.execute_journey(db, order, inject_inventory_503=True)

        if incident and incident.rca_report:
            rca = incident.rca_report
            evidence_list = json.loads(rca.observed_evidence) if rca.observed_evidence else []
            rca_resp = RCAReportResponse(
                rca_id=rca.rca_id,
                incident_id=rca.incident_id,
                failure_category=rca.failure_category,
                affected_service=rca.affected_service,
                observed_evidence=evidence_list,
                probable_root_cause=rca.probable_root_cause,
                evidence_strength=rca.evidence_strength,
                corroborating_signals_count=rca.corroborating_signals_count,
                recommended_action=rca.recommended_action,
                risk_level=rca.risk_level,
                explanation=rca.explanation,
                model_source=rca.model_source,
                prompt_tokens=rca.prompt_tokens,
                created_at=rca.created_at
            )

        # If auto_resolve requested, execute the self-healing retry immediately
        if request.auto_resolve and incident:
            idemp_key = f"idemp_{order.order_id}_INVENTORY_1"
            action = resolution_service.execute_resolution(
                db=db,
                incident_id=incident.incident_id,
                action_type="RETRY_WITH_BACKOFF",
                idempotency_key=idemp_key
            )
            if action.verification_passed and action.execution_status == "SUCCEEDED":
                background_tasks.add_task(order_service.resume_remaining_stages_background, action.order_id)

            resolution_resp = ResolutionActionResponse(
                action_id=action.action_id,
                incident_id=action.incident_id,
                order_id=action.order_id,
                action_type=action.action_type,
                attempt_number=action.attempt_number,
                backoff_delay_sec=action.backoff_delay_sec,
                execution_status=action.execution_status,
                verification_passed=action.verification_passed,
                verification_details=action.verification_details,
                order_status=order.order_status,
                completed_at=action.completed_at
            )
            msg = f"Scenario 1 executed: Injected HTTP 503, advisory RCA completed, policy retry succeeded, inventory verified, resumed downstream stages. Order: {order.order_id}"
        else:
            msg = f"Scenario 1 initiated: Injected HTTP 503 at Inventory, detected incident, and generated advisory RCA. Ready for resolution. Order: {order.order_id}"

    elif scenario == "SCENARIO_2_SLA_DELAY":
        order, incident = order_service.execute_journey(db, order, inject_fulfilment_delay=True)

        if incident and incident.rca_report:
            rca = incident.rca_report
            evidence_list = json.loads(rca.observed_evidence) if rca.observed_evidence else []
            rca_resp = RCAReportResponse(
                rca_id=rca.rca_id,
                incident_id=rca.incident_id,
                failure_category=rca.failure_category,
                affected_service=rca.affected_service,
                observed_evidence=evidence_list,
                probable_root_cause=rca.probable_root_cause,
                evidence_strength=rca.evidence_strength,
                corroborating_signals_count=rca.corroborating_signals_count,
                recommended_action=rca.recommended_action,
                risk_level=rca.risk_level,
                explanation=rca.explanation,
                model_source=rca.model_source,
                prompt_tokens=rca.prompt_tokens,
                created_at=rca.created_at
            )

        resolution_resp = None
        operator_alert = {
            "stage": "FULFILMENT",
            "elapsed_duration_ms": 10000,
            "sla_threshold_ms": 5000,
            "breach_ms": 5000,
            "alert_status": "AWAITING_OPERATOR_INVESTIGATION",
            "action_required": "OPERATOR_REVIEW",
            "prohibited_actions": ["CANCEL_ORDER", "REASSIGN_WAREHOUSE", "RETRY_WITH_BACKOFF"],
            "authorized_action": "EXPEDITE_FULFILMENT"
        }
        msg = (
            f"Scenario 2 executed: Injected 10000ms fulfilment latency, detected SLA breach "
            f"(threshold: 5000ms, breach: +5000ms). Order marked DELAYED. Operator alert issued. Order: {order.order_id}"
        )

    elif scenario == "SCENARIO_3_HARD_REJECTION":
        order, incident = order_service.execute_journey(db, order, inject_inventory_422=True)

        if incident and incident.rca_report:
            rca = incident.rca_report
            evidence_list = json.loads(rca.observed_evidence) if rca.observed_evidence else []
            rca_resp = RCAReportResponse(
                rca_id=rca.rca_id,
                incident_id=rca.incident_id,
                failure_category=rca.failure_category,
                affected_service=rca.affected_service,
                observed_evidence=evidence_list,
                probable_root_cause=rca.probable_root_cause,
                evidence_strength=rca.evidence_strength,
                corroborating_signals_count=rca.corroborating_signals_count,
                recommended_action=rca.recommended_action,
                risk_level=rca.risk_level,
                explanation=rca.explanation,
                model_source=rca.model_source,
                prompt_tokens=rca.prompt_tokens,
                created_at=rca.created_at
            )

        if incident and incident.approvals:
            app_record = incident.approvals[0]
            params = json.loads(app_record.action_parameters) if app_record.action_parameters else None
            approval_resp = ApprovalResponse(
                approval_id=app_record.approval_id,
                incident_id=app_record.incident_id,
                order_id=app_record.order_id,
                selected_action=app_record.selected_action,
                action_parameters=params,
                risk_level=app_record.risk_level,
                decision=app_record.decision,
                requested_at=app_record.requested_at
            )

        msg = (
            f"Scenario 3 executed: Injected HTTP 422 Out-of-Stock rejection at Inventory. "
            f"Order remains in PROCESSING (inventory blocked). Queued in Operator Approval Queue. Order: {order.order_id}"
        )

    db.refresh(order)
    events = [OrderEventResponse.model_validate(e) for e in order.events]

    data = SimulationScenarioResponse(
        scenario_key=scenario,
        order=OrderResponse.model_validate(order),
        incident=IncidentResponse.model_validate(incident) if incident else None,
        rca=rca_resp,
        resolution=resolution_resp,
        approval=approval_resp,
        events=events,
        operator_alert=operator_alert,
        message=msg,
        selected_outcome=selected_outcome,
        outcome_reason=outcome_reason,
        demo_probabilities=DEMO_PROBABILITIES
    )

    return ApiResponse(success=True, data=data, message=msg)


@router.post(
    "/simulation/reset-demo-session",
    response_model=ApiResponse[DemoSessionResetResponse],
    summary="Safely Reset Live Demo Session Records",
    description="Purges ONLY orders and linked events explicitly created during the specified demo session. Historical project records are preserved."
)
def reset_demo_session(
    request: DemoSessionResetRequest,
    db: Session = Depends(get_db)
):
    session_id = request.demo_session_id.strip() if request.demo_session_id else ""
    if not session_id:
        raise HTTPException(status_code=400, detail="demo_session_id is required.")

    # Match orders created under this specific demo session
    demo_orders = db.query(Order).filter(
        Order.demo_session_id == session_id,
        Order.is_demo_order == True
    ).all()

    order_ids = [o.order_id for o in demo_orders]
    corr_ids = [o.correlation_id for o in demo_orders]
    count = len(order_ids)

    if count > 0:
        # Delete linked audit logs
        db.query(AuditLog).filter(AuditLog.order_id.in_(order_ids)).delete(synchronize_session=False)
        db.query(AuditLog).filter(AuditLog.correlation_id.in_(corr_ids)).delete(synchronize_session=False)

        # Delete incidents and children
        incidents = db.query(Incident).filter(Incident.order_id.in_(order_ids)).all()
        inc_ids = [i.incident_id for i in incidents]
        if inc_ids:
            db.query(OperatorApproval).filter(OperatorApproval.incident_id.in_(inc_ids)).delete(synchronize_session=False)
            db.query(ResolutionAction).filter(ResolutionAction.incident_id.in_(inc_ids)).delete(synchronize_session=False)
            db.query(RCAReport).filter(RCAReport.incident_id.in_(inc_ids)).delete(synchronize_session=False)
            db.query(Incident).filter(Incident.incident_id.in_(inc_ids)).delete(synchronize_session=False)

        db.query(OperatorApproval).filter(OperatorApproval.order_id.in_(order_ids)).delete(synchronize_session=False)
        db.query(ResolutionAction).filter(ResolutionAction.order_id.in_(order_ids)).delete(synchronize_session=False)
        db.query(OrderEvent).filter(OrderEvent.order_id.in_(order_ids)).delete(synchronize_session=False)
        db.query(Order).filter(Order.order_id.in_(order_ids)).delete(synchronize_session=False)

        audit_service.log_event(
            db=db,
            correlation_id=f"session-reset-{uuid.uuid4().hex[:8]}",
            order_id=None,
            event_type="DEMO_SESSION_RESET",
            actor_type="OPERATOR",
            actor_id="OPERATOR:DEMO",
            summary=f"Demo session '{session_id}' reset. Purged {count} live demonstration order(s). Historical data untouched.",
            metadata={"purged_orders_count": count, "session_id": session_id}
        )

        db.commit()

    return ApiResponse(
        success=True,
        data=DemoSessionResetResponse(
            demo_session_id=session_id,
            cleared_orders_count=count,
            message=f"Demo session successfully reset. Removed {count} live demonstration order(s). Historical database records remain untouched."
        ),
        message=f"Demo session '{session_id}' cleared ({count} order(s))."
    )
