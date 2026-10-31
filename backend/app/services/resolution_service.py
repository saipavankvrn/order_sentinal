import uuid
from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy.orm import Session
from backend.app.models.order import Order, Incident, ResolutionAction, OrderEvent
from backend.app.policies.policy_engine import policy_engine
from backend.app.services.simulator import simulator
from backend.app.services.audit_service import audit_service
from backend.app.core.logging import logger


class ResolutionService:
    """Intelligent Resolution Engine with deterministic policy enforcement,
    database idempotency, and downstream domain state verification.
    """

    @staticmethod
    def execute_resolution(
        db: Session,
        incident_id: str,
        action_type: str,
        idempotency_key: str,
        force_fail_downstream: bool = False
    ) -> ResolutionAction:
        from backend.app.services.order_service import order_service

        # Step 1: Database Idempotency Check (Primary Authority)
        existing_action = db.query(ResolutionAction).filter_by(idempotency_key=idempotency_key).first()
        if existing_action:
            if existing_action.action_type == action_type:
                logger.info(f"Idempotent execution detected for key {idempotency_key}. Returning cached action.")
                existing_action._is_idempotent_replay = True
                return existing_action
            else:
                logger.warning(f"Conflicting action for idempotency key {idempotency_key}: {existing_action.action_type} vs {action_type}")
                raise HTTPException(
                    status_code=409,
                    detail=f"Idempotency collision: Key '{idempotency_key}' already used with conflicting action '{existing_action.action_type}'."
                )

        # Step 2: Retrieve Incident and Linked Order
        incident = db.query(Incident).filter_by(incident_id=incident_id).first()
        if not incident:
            raise HTTPException(status_code=404, detail=f"Incident with ID '{incident_id}' not found.")

        order = db.query(Order).filter_by(order_id=incident.order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail=f"Linked order '{incident.order_id}' not found.")

        # Step 3: Policy-as-Code Authorization
        authorized, reason, backoff_sec, escalate = policy_engine.evaluate_action(
            incident=incident,
            proposed_action=action_type
        )

        if not authorized:
            if escalate:
                incident.incident_status = "ESCALATED"
                db.commit()
                audit_service.log_event(
                    db=db,
                    correlation_id=order.correlation_id,
                    order_id=order.order_id,
                    incident_id=incident.incident_id,
                    event_type="INCIDENT_ESCALATED",
                    actor_type="SYSTEM",
                    actor_id="POLICY_ENGINE",
                    summary=f"Incident escalated: {reason}",
                    metadata={"retry_count": incident.retry_count, "max_retries": incident.max_retries}
                )
            raise HTTPException(status_code=400, detail=reason)

        # Step 4: Sequence Attempt Number (Strictly 1, 2, or 3)
        attempt_number = incident.retry_count + 1
        incident.retry_count = attempt_number
        incident.incident_status = "RESOLVING"

        action_id = f"ACT-{uuid.uuid4().hex[:8].upper()}"
        action = ResolutionAction(
            action_id=action_id,
            incident_id=incident.incident_id,
            order_id=order.order_id,
            action_type=action_type,
            idempotency_key=idempotency_key,
            attempt_number=attempt_number,
            backoff_delay_sec=backoff_sec,
            execution_status="EXECUTING"
        )
        db.add(action)
        db.commit()

        audit_service.log_event(
            db=db,
            correlation_id=order.correlation_id,
            order_id=order.order_id,
            incident_id=incident.incident_id,
            event_type="ACTION_DISPATCHED",
            actor_type="SYSTEM",
            actor_id="RESOLUTION_ENGINE",
            summary=f"Dispatched retry attempt {attempt_number} with {backoff_sec}s backoff for {incident.stage}.",
            metadata={"idempotency_key": idempotency_key, "attempt_number": attempt_number}
        )

        # Step 5: Execute Action through Simulated Downstream Adapter
        action.execution_status = "VERIFYING"
        db.commit()

        if action_type in ["EXPEDITE_FULFILMENT", "EXPEDITE_FULFILMENT_QUEUE"] or incident.stage == "FULFILMENT":
            http_status, duration_ms, event_status, err_code, err_msg = simulator.expedite_fulfilment(
                order_id=order.order_id,
                force_fail=force_fail_downstream
            )
            stage_name = "FULFILMENT"
            service_name = "fulfilment_service"
            endpoint = "/v1/fulfilment/expedite"
            payload_summary = f"Expedite priority queue elevation for {order.order_id}"
            verified, verification_details = simulator.verify_fulfilment_state(order.order_id)
        else:
            http_status, duration_ms, event_status, err_code, err_msg = simulator.reserve_inventory(
                order_id=order.order_id,
                sku=order.product_sku,
                is_retry=True,
                force_fail=force_fail_downstream
            )
            stage_name = "INVENTORY"
            service_name = "inventory_service"
            endpoint = "/v1/inventory/reserve"
            payload_summary = f"Retry attempt {attempt_number} for {order.product_sku}"
            verified, verification_details = simulator.verify_inventory_state(order.order_id)

        # Record action event in order_events timeline
        action_event = OrderEvent(
            event_id=f"EVT-{uuid.uuid4().hex[:8].upper()}",
            order_id=order.order_id,
            correlation_id=order.correlation_id,
            stage=stage_name,
            service_name=service_name,
            endpoint=endpoint,
            http_method="POST",
            http_status=http_status,
            duration_ms=duration_ms,
            event_status=event_status,
            payload_summary=payload_summary,
            error_code=err_code if err_code else None,
            error_message=err_msg if err_msg else None
        )
        db.add(action_event)

        # Step 6: Downstream Domain State Verification Probe
        # Do not trust HTTP 200 alone; assert domain store mutation
        now = datetime.now(timezone.utc)
        if http_status == 200 and verified:
            action.verification_passed = True
            action.verification_details = verification_details
            action.execution_status = "SUCCEEDED"
            action.completed_at = now

            incident.incident_status = "RESOLVED"
            incident.resolved_at = now

            if incident.stage == "INVENTORY":
                order.inventory_status = "RESERVED"
            elif incident.stage == "FULFILMENT":
                order.fulfilment_status = "ALLOCATED"

            # Transition order from DELAYED or PENDING back to PROCESSING per state machine
            order.order_status = "PROCESSING"
            db.commit()

            audit_service.log_event(
                db=db,
                correlation_id=order.correlation_id,
                order_id=order.order_id,
                incident_id=incident.incident_id,
                event_type="VERIFICATION_PASSED",
                actor_type="SYSTEM",
                actor_id="VERIFICATION_PROBE",
                summary=f"{incident.stage} resolution verified: {verification_details}",
                metadata={"status": "CONFIRMED"}
            )

            audit_service.log_event(
                db=db,
                correlation_id=order.correlation_id,
                order_id=order.order_id,
                incident_id=incident.incident_id,
                event_type="INCIDENT_RESOLVED",
                actor_type="SYSTEM",
                actor_id="RESOLUTION_ENGINE",
                summary=f"Incident {incident.incident_id} resolved after verified {action_type}.",
                metadata={"resolved_at": now.isoformat()}
            )
        else:
            action.verification_passed = False
            action.verification_details = verification_details if not verified else err_msg
            action.execution_status = "FAILED"
            action.completed_at = now

            if incident.retry_count >= incident.max_retries:
                incident.incident_status = "ESCALATED"
                audit_service.log_event(
                    db=db,
                    correlation_id=order.correlation_id,
                    order_id=order.order_id,
                    incident_id=incident.incident_id,
                    event_type="INCIDENT_ESCALATED",
                    actor_type="SYSTEM",
                    actor_id="POLICY_ENGINE",
                    summary=f"Max attempts ({incident.max_retries}) exhausted without recovery. Incident escalated to operator.",
                    metadata={"attempts": incident.retry_count}
                )

            db.commit()

        db.refresh(action)
        return action


resolution_service = ResolutionService()

