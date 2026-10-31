import json
import uuid
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timezone
from fastapi import HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from backend.app.models.order import Order, OrderEvent, Incident, OperatorApproval
from backend.app.schemas.approval import ApprovalDecisionRequest, ApprovalResponse, ApprovalDecisionResponse
from backend.app.schemas.order import OrderResponse
from backend.app.schemas.incident import IncidentResponse, RCAReportResponse
from backend.app.services.simulator import simulator
from backend.app.services.order_service import order_service
from backend.app.services.audit_service import audit_service
from backend.app.core.logging import logger


class ApprovalService:
    """Coordinates Human-in-the-Loop approval workflows for hard business rejections."""

    @classmethod
    def list_pending_approvals(
        cls,
        db: Session,
        demo_session_id: Optional[str] = None,
        is_demo: Optional[bool] = None
    ) -> List[ApprovalResponse]:
        """Returns all approval requests currently awaiting human operator decision."""
        query = db.query(OperatorApproval).filter(
            OperatorApproval.decision == "PENDING"
        )
        if is_demo is True or demo_session_id is not None:
            query = query.join(Order, OperatorApproval.order_id == Order.order_id)
            if is_demo is True:
                query = query.filter(Order.is_demo_order == True)
            if demo_session_id:
                query = query.filter(Order.demo_session_id == demo_session_id)
        elif is_demo is False:
            query = query.join(Order, OperatorApproval.order_id == Order.order_id).filter(
                (Order.is_demo_order == False) | (Order.is_demo_order == None)
            )

        approvals = query.order_by(OperatorApproval.requested_at.desc()).all()

        results = []
        for app in approvals:
            results.append(cls._build_approval_response(db, app))
        return results

    @classmethod
    def get_approval(cls, db: Session, approval_id: str) -> ApprovalResponse:
        """Retrieves a single approval record with linked order, incident, and RCA details."""
        approval = db.query(OperatorApproval).filter_by(approval_id=approval_id).first()
        if not approval:
            raise HTTPException(status_code=404, detail=f"Approval request '{approval_id}' not found.")
        return cls._build_approval_response(db, approval)

    @classmethod
    def submit_decision(
        cls,
        db: Session,
        approval_id: str,
        request: ApprovalDecisionRequest,
        background_tasks: Optional[BackgroundTasks] = None
    ) -> Tuple[ApprovalDecisionResponse, str]:
        """Processes an operator decision (APPROVED or REJECTED) with parameter validation,
        simulated adapter execution, downstream domain state verification, and audit trail logging.
        """
        # Guard: Check for unsupported override
        decision_upper = request.decision.upper()
        if decision_upper == "OVERRIDE":
            raise HTTPException(
                status_code=400,
                detail="Unsupported decision: OVERRIDE is excluded from MVP scope. Supported decisions: APPROVED, REJECTED."
            )
        if decision_upper not in ["APPROVED", "REJECTED"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid decision '{request.decision}'. Supported decisions are APPROVED or REJECTED."
            )

        approval = db.query(OperatorApproval).filter_by(approval_id=approval_id).first()
        if not approval:
            raise HTTPException(status_code=404, detail=f"Approval request '{approval_id}' not found.")

        order = db.query(Order).filter_by(order_id=approval.order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail=f"Linked order '{approval.order_id}' not found.")

        incident = db.query(Incident).filter_by(incident_id=approval.incident_id).first()
        if not incident:
            raise HTTPException(status_code=404, detail=f"Linked incident '{approval.incident_id}' not found.")

        # Idempotency Guard: Check if already decided
        if approval.decision != "PENDING":
            if approval.decision == decision_upper:
                # Idempotent replay: return cached state without duplicate execution
                logger.info(f"Idempotent replay of decision '{decision_upper}' for approval {approval_id}")
                cached_params = json.loads(approval.action_parameters) if approval.action_parameters else {}
                data = ApprovalDecisionResponse(
                    approval_id=approval.approval_id,
                    incident_id=approval.incident_id,
                    decision=approval.decision,
                    selected_action=approval.selected_action,
                    action_parameters=cached_params,
                    execution_status="SUCCEEDED" if approval.decision == "APPROVED" else "REJECTED",
                    verification_passed=True if approval.decision == "APPROVED" else False,
                    order_status=order.order_status,
                    current_stage=order.current_stage
                )
                msg = f"Approval decision already recorded as {approval.decision} (idempotent replay)."
                return data, msg
            else:
                # Conflicting decision on already finalized approval
                raise HTTPException(
                    status_code=409,
                    detail=f"Approval request '{approval_id}' has already been decided as '{approval.decision}'. Conflicting decision rejected."
                )

        now = datetime.now(timezone.utc)

        # Branch 1: Operator REJECTED
        if decision_upper == "REJECTED":
            approval.decision = "REJECTED"
            approval.operator_id = request.operator_id
            approval.operator_name = request.operator_name
            approval.operator_notes = request.operator_notes or "Rejected by operator"
            approval.selected_action = request.selected_action or "REJECT_ORDER"
            approval.decided_at = now

            incident.incident_status = "REJECTED"
            order.order_status = "FAILED"
            order.inventory_status = "REJECTED"
            db.commit()

            audit_service.log_event(
                db=db,
                correlation_id=order.correlation_id,
                order_id=order.order_id,
                incident_id=incident.incident_id,
                event_type="OPERATOR_REJECTED",
                actor_type="OPERATOR",
                actor_id=request.operator_id,
                summary=f"Operator {request.operator_name} rejected approval {approval_id}. Notes: {request.operator_notes}",
                metadata={"approval_id": approval.approval_id, "decision": "REJECTED", "notes": request.operator_notes}
            )
            audit_service.log_event(
                db=db,
                correlation_id=order.correlation_id,
                order_id=order.order_id,
                incident_id=incident.incident_id,
                event_type="ORDER_FAILED",
                actor_type="SYSTEM",
                actor_id="APPROVAL_SERVICE",
                summary=f"Order marked FAILED following operator rejection of approval {approval_id}.",
                metadata={"final_stage": order.current_stage, "reason": request.operator_notes or "Operator rejected"}
            )

            data = ApprovalDecisionResponse(
                approval_id=approval.approval_id,
                incident_id=approval.incident_id,
                decision="REJECTED",
                selected_action=approval.selected_action,
                action_parameters={},
                execution_status="REJECTED",
                verification_passed=False,
                order_status="FAILED",
                current_stage=order.current_stage
            )
            msg = "Operator rejected approval request. Incident marked REJECTED and order transitioned to FAILED."
            return data, msg

        # Branch 2: Operator APPROVED
        params = request.action_parameters or (json.loads(approval.action_parameters) if approval.action_parameters else {})
        sub_sku = params.get("substitute_sku")
        alt_hub = params.get("alternate_hub")

        # Step 2a: Adapter Parameter Validation
        valid, val_reason = simulator.validate_substitution_parameters(
            substitute_sku=sub_sku,
            alternate_hub=alt_hub,
            original_sku=order.product_sku
        )
        if not valid:
            logger.warning(f"Parameter validation failed for approval {approval_id}: {val_reason}")
            raise HTTPException(status_code=400, detail=f"Parameter validation failed: {val_reason}")

        # Step 2b: Execute Substitution through Simulated Adapter
        http_status, duration_ms, event_status, err_code, err_msg = simulator.execute_substitution(
            order_id=order.order_id,
            substitute_sku=sub_sku,
            alternate_hub=alt_hub
        )

        # Record action event in order_events timeline
        action_event = OrderEvent(
            event_id=f"EVT-{uuid.uuid4().hex[:8].upper()}",
            order_id=order.order_id,
            correlation_id=order.correlation_id,
            stage="INVENTORY",
            service_name="inventory_service",
            endpoint="/v1/inventory/substitute",
            http_method="POST",
            http_status=http_status,
            duration_ms=duration_ms,
            event_status=event_status,
            payload_summary=f"Approved substitution: SKU {sub_sku} at hub {alt_hub}",
            error_code=err_code if err_code else None,
            error_message=err_msg if err_msg else None
        )
        db.add(action_event)

        # Step 2c: Downstream State Verification Probe
        # Never trust HTTP 200 alone; probe inventory domain store
        verified, verification_details = simulator.verify_inventory_state(order.order_id)
        if http_status != 200 or not verified:
            # Verification probe failed! Recovery blocked.
            logger.error(f"Downstream state verification probe failed for approval {approval_id}: {verification_details}")
            db.commit()
            data = ApprovalDecisionResponse(
                approval_id=approval.approval_id,
                incident_id=approval.incident_id,
                decision="PENDING",
                selected_action=request.selected_action or approval.selected_action,
                action_parameters=params,
                execution_status="FAILED",
                verification_passed=False,
                order_status=order.order_status,
                current_stage=order.current_stage
            )
            msg = f"Execution failed: Downstream state verification did not pass ({verification_details})."
            return data, msg

        # Step 2d: Successful verified recovery
        approval.decision = "APPROVED"
        approval.operator_id = request.operator_id
        approval.operator_name = request.operator_name
        approval.operator_notes = request.operator_notes or "Substitution approved"
        approval.selected_action = request.selected_action or "SUBSTITUTE_SKU_AND_REALLOCATE"
        approval.action_parameters = json.dumps(params)
        approval.decided_at = now

        incident.incident_status = "RESOLVED"
        incident.resolved_at = now

        order.inventory_status = "RESERVED"
        order.product_sku = sub_sku
        order.order_status = "PROCESSING"
        # Preserve current_stage as INVENTORY so resume_remaining_stages claims it and executes FULFILMENT (Stage 5)
        db.commit()

        audit_service.log_event(
            db=db,
            correlation_id=order.correlation_id,
            order_id=order.order_id,
            incident_id=incident.incident_id,
            event_type="OPERATOR_APPROVED",
            actor_type="OPERATOR",
            actor_id=request.operator_id,
            summary=f"Operator {request.operator_name} approved substitution with SKU {sub_sku} at hub {alt_hub}.",
            metadata={"approval_id": approval.approval_id, "params": params, "notes": request.operator_notes}
        )
        audit_service.log_event(
            db=db,
            correlation_id=order.correlation_id,
            order_id=order.order_id,
            incident_id=incident.incident_id,
            event_type="VERIFICATION_PASSED",
            actor_type="SYSTEM",
            actor_id="VERIFICATION_PROBE",
            summary=f"Downstream inventory state verified: {verification_details}",
            metadata={"status": "CONFIRMED", "substitute_sku": sub_sku, "hub": alt_hub}
        )
        audit_service.log_event(
            db=db,
            correlation_id=order.correlation_id,
            order_id=order.order_id,
            incident_id=incident.incident_id,
            event_type="INCIDENT_RESOLVED",
            actor_type="SYSTEM",
            actor_id="APPROVAL_SERVICE",
            summary=f"Incident {incident.incident_id} resolved following verified substitution. Order resumed in PROCESSING.",
            metadata={"resolved_at": now.isoformat()}
        )

        # Step 2e: Schedule decoupled background journey continuation post-response
        if background_tasks:
            background_tasks.add_task(order_service.resume_remaining_stages_background, order.order_id)

        data = ApprovalDecisionResponse(
            approval_id=approval.approval_id,
            incident_id=approval.incident_id,
            decision="APPROVED",
            selected_action=approval.selected_action,
            action_parameters=params,
            execution_status="SUCCEEDED",
            verification_passed=True,
            order_status="PROCESSING",
            current_stage="FULFILMENT"
        )
        msg = "Operator decision approved, parameters validated, executed, and verified. Order continues in PROCESSING."
        return data, msg

    @classmethod
    def _build_approval_response(cls, db: Session, approval: OperatorApproval) -> ApprovalResponse:
        """Helper to build ApprovalResponse with embedded order and incident context."""
        params = json.loads(approval.action_parameters) if approval.action_parameters else None
        order = db.query(Order).filter_by(order_id=approval.order_id).first()
        incident = db.query(Incident).filter_by(incident_id=approval.incident_id).first()

        rca_resp = None
        if incident and incident.rca_report:
            rca = incident.rca_report
            ev_list = json.loads(rca.observed_evidence) if rca.observed_evidence else []
            rca_resp = RCAReportResponse(
                rca_id=rca.rca_id,
                incident_id=rca.incident_id,
                failure_category=rca.failure_category,
                affected_service=rca.affected_service,
                observed_evidence=ev_list,
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

        return ApprovalResponse(
            approval_id=approval.approval_id,
            incident_id=approval.incident_id,
            order_id=approval.order_id,
            selected_action=approval.selected_action,
            action_parameters=params,
            risk_level=approval.risk_level,
            decision=approval.decision,
            operator_id=approval.operator_id,
            operator_name=approval.operator_name,
            operator_notes=approval.operator_notes,
            requested_at=approval.requested_at,
            decided_at=approval.decided_at,
            order=OrderResponse.model_validate(order) if order else None,
            incident=IncidentResponse.model_validate(incident) if incident else None,
            rca_report=rca_resp
        )


approval_service = ApprovalService()
