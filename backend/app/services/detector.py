import json
import uuid
from typing import Tuple, Optional
from sqlalchemy.orm import Session
from backend.app.models.order import Order, OrderEvent, Incident, RCAReport, SystemPolicy, OperatorApproval
from backend.app.ai.gemini_rca import rca_engine
from backend.app.services.audit_service import audit_service
from backend.app.core.logging import logger


class FailureDetectionEngine:
    """Deterministic failure detection engine and incident lifecycle manager."""

    @staticmethod
    def evaluate_stage_sla(
        db: Session,
        stage: str,
        duration_ms: int
    ) -> Tuple[bool, int, int]:
        """Compares stage execution duration against configured demo SLA threshold in system_policies.
        Returns: (is_breach: bool, sla_threshold_ms: int, breach_ms: int)
        """
        sla_key = f"SLA_STAGE_{stage}_MS"
        policy = db.query(SystemPolicy).filter_by(policy_key=sla_key).first()
        sla_threshold_ms = int(policy.policy_value) if policy else 5000
        is_breach = duration_ms > sla_threshold_ms
        breach_ms = max(0, duration_ms - sla_threshold_ms)
        return is_breach, sla_threshold_ms, breach_ms

    @staticmethod
    def process_telemetry_event(
        db: Session,
        order: Order,
        event: OrderEvent
    ) -> Optional[Incident]:
        """Evaluates event for failure conditions and dispatches incident creation."""
        # Detect HTTP 503 transient failure
        if event.http_status == 503:
            logger.info(f"Deterministic detector flagged HTTP 503 on stage {event.stage} for order {order.order_id}")

            incident_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
            incident = Incident(
                incident_id=incident_id,
                order_id=order.order_id,
                stage=event.stage,
                service_name=event.service_name,
                failure_category="API_ERROR",
                failure_type="HTTP_503",
                incident_status="DETECTED",
                severity="LOW",
                retry_count=0,
                max_retries=3
            )
            db.add(incident)
            db.commit()
            db.refresh(incident)

            # Audit log incident creation
            audit_service.log_event(
                db=db,
                correlation_id=order.correlation_id,
                order_id=order.order_id,
                incident_id=incident.incident_id,
                event_type="INCIDENT_DETECTED",
                actor_type="SYSTEM",
                actor_id="DETECTOR_ENGINE",
                summary=f"HTTP 503 failure detected at {event.stage} ({event.service_name}). Incident created.",
                metadata={
                    "stage": event.stage,
                    "service": event.service_name,
                    "http_status": event.http_status,
                    "error_message": event.error_message
                }
            )

            # State transition: DETECTED -> ANALYZING before RCA processing
            incident.incident_status = "ANALYZING"
            db.commit()
            db.refresh(incident)

            # Generate advisory RCA
            recent_events = [
                {
                    "stage": e.stage,
                    "endpoint": e.endpoint,
                    "http_status": e.http_status,
                    "duration_ms": e.duration_ms,
                    "error_message": e.error_message
                }
                for e in order.events[-5:]
            ]

            rca_data = rca_engine.analyze_incident(
                incident_id=incident.incident_id,
                order_id=order.order_id,
                stage=event.stage,
                service_name=event.service_name,
                failure_type=incident.failure_type,
                recent_events=recent_events,
                error_message=event.error_message or ""
            )

            rca_id = f"RCA-{uuid.uuid4().hex[:8].upper()}"
            rca_record = RCAReport(
                rca_id=rca_id,
                incident_id=incident.incident_id,
                failure_category=rca_data["failure_category"],
                affected_service=rca_data["affected_service"],
                observed_evidence=json.dumps(rca_data["observed_evidence"]),
                probable_root_cause=rca_data["probable_root_cause"],
                evidence_strength=rca_data["evidence_strength"],
                corroborating_signals_count=rca_data["corroborating_signals_count"],
                recommended_action=rca_data["recommended_action"],
                risk_level=rca_data["risk_level"],
                explanation=rca_data["explanation"],
                model_source=rca_data["model_source"],
                prompt_tokens=rca_data.get("prompt_tokens", 0)
            )
            db.add(rca_record)
            db.commit()

            audit_service.log_event(
                db=db,
                correlation_id=order.correlation_id,
                order_id=order.order_id,
                incident_id=incident.incident_id,
                event_type="RCA_COMPLETED",
                actor_type="AI_AGENT",
                actor_id=rca_data["model_source"],
                summary=f"Advisory RCA completed: Recommended {rca_data['recommended_action']} ({rca_data['evidence_strength']} evidence).",
                metadata=rca_data
            )

            return incident

        # Detect HTTP 422 permanent business rejection (Scenario 3: Out-of-Stock)
        if event.http_status == 422:
            logger.info(f"Deterministic detector flagged HTTP 422 Out-of-Stock on stage {event.stage} for order {order.order_id}")

            incident_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
            incident = Incident(
                incident_id=incident_id,
                order_id=order.order_id,
                stage=event.stage,
                service_name=event.service_name,
                failure_category="ORDER_REJECTION",
                failure_type="OUT_OF_STOCK",
                incident_status="DETECTED",
                severity="HIGH",
                retry_count=0,
                max_retries=0
            )
            db.add(incident)
            db.commit()
            db.refresh(incident)

            # Audit log incident creation
            audit_service.log_event(
                db=db,
                correlation_id=order.correlation_id,
                order_id=order.order_id,
                incident_id=incident.incident_id,
                event_type="INCIDENT_DETECTED",
                actor_type="SYSTEM",
                actor_id="DETECTOR_ENGINE",
                summary=f"Hard business rejection (OUT_OF_STOCK) detected at {event.stage} ({event.service_name}). Order remains in PROCESSING. Stage blocked.",
                metadata={
                    "stage": event.stage,
                    "service": event.service_name,
                    "http_status": event.http_status,
                    "error_message": event.error_message
                }
            )

            # State transition: DETECTED -> ANALYZING before RCA processing
            incident.incident_status = "ANALYZING"
            db.commit()
            db.refresh(incident)

            # Generate advisory RCA
            recent_events = [
                {
                    "stage": e.stage,
                    "endpoint": e.endpoint,
                    "http_status": e.http_status,
                    "duration_ms": e.duration_ms,
                    "error_message": e.error_message
                }
                for e in order.events[-5:]
            ]

            rca_data = rca_engine.analyze_incident(
                incident_id=incident.incident_id,
                order_id=order.order_id,
                stage=event.stage,
                service_name=event.service_name,
                failure_type=incident.failure_type,
                recent_events=recent_events,
                error_message=event.error_message or ""
            )

            rca_id = f"RCA-{uuid.uuid4().hex[:8].upper()}"
            rca_record = RCAReport(
                rca_id=rca_id,
                incident_id=incident.incident_id,
                failure_category=rca_data["failure_category"],
                affected_service=rca_data["affected_service"],
                observed_evidence=json.dumps(rca_data["observed_evidence"]),
                probable_root_cause=rca_data["probable_root_cause"],
                evidence_strength=rca_data["evidence_strength"],
                corroborating_signals_count=rca_data["corroborating_signals_count"],
                recommended_action=rca_data["recommended_action"],
                risk_level=rca_data["risk_level"],
                explanation=rca_data["explanation"],
                model_source=rca_data["model_source"],
                prompt_tokens=rca_data.get("prompt_tokens", 0)
            )
            db.add(rca_record)
            db.commit()

            audit_service.log_event(
                db=db,
                correlation_id=order.correlation_id,
                order_id=order.order_id,
                incident_id=incident.incident_id,
                event_type="RCA_COMPLETED",
                actor_type="AI_AGENT",
                actor_id=rca_data["model_source"],
                summary=f"Advisory RCA completed: Recommended {rca_data['recommended_action']} ({rca_data['risk_level']} risk). Routed to Human Approval Queue.",
                metadata=rca_data
            )

            # Route to Human Approval Queue: create operator_approvals record
            approval_id = f"APP-{uuid.uuid4().hex[:8].upper()}"
            suggested_params = {
                "substitute_sku": f"{order.product_sku}-ALT",
                "alternate_hub": "HUB-EAST-02"
            }
            approval = OperatorApproval(
                approval_id=approval_id,
                incident_id=incident.incident_id,
                order_id=order.order_id,
                selected_action=rca_data["recommended_action"],
                action_parameters=json.dumps(suggested_params),
                risk_level="HIGH",
                decision="PENDING"
            )
            db.add(approval)

            # Transition incident status: ANALYZING -> PENDING_APPROVAL
            incident.incident_status = "PENDING_APPROVAL"
            db.commit()
            db.refresh(incident)

            audit_service.log_event(
                db=db,
                correlation_id=order.correlation_id,
                order_id=order.order_id,
                incident_id=incident.incident_id,
                event_type="APPROVAL_REQUESTED",
                actor_type="SYSTEM",
                actor_id="DETECTOR_ENGINE",
                summary=f"Approval request {approval_id} queued for operator review. Risk level: HIGH. Candidate action: {approval.selected_action}.",
                metadata={
                    "approval_id": approval_id,
                    "selected_action": approval.selected_action,
                    "suggested_parameters": suggested_params,
                    "risk_level": "HIGH"
                }
            )

            return incident

        # Detect SLA delay (duration exceeds configured illustrative demo SLA threshold)
        is_breach, sla_threshold_ms, breach_ms = FailureDetectionEngine.evaluate_stage_sla(
            db=db,
            stage=event.stage,
            duration_ms=event.duration_ms
        )

        if is_breach:
            logger.warning(
                f"SLA breach detected on stage {event.stage} for order {order.order_id}: "
                f"{event.duration_ms}ms > {sla_threshold_ms}ms (+{breach_ms}ms breach)"
            )

            # State transition: PROCESSING -> DELAYED per documented state machine
            order.order_status = "DELAYED"
            db.commit()

            incident_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
            incident = Incident(
                incident_id=incident_id,
                order_id=order.order_id,
                stage=event.stage,
                service_name=event.service_name,
                failure_category="ORDER_DELAY",
                failure_type="SLA_BREACH",
                incident_status="DETECTED",
                severity="MEDIUM",
                retry_count=0,
                max_retries=1
            )
            db.add(incident)
            db.commit()
            db.refresh(incident)

            # Audit log incident creation
            audit_service.log_event(
                db=db,
                correlation_id=order.correlation_id,
                order_id=order.order_id,
                incident_id=incident.incident_id,
                event_type="INCIDENT_DETECTED",
                actor_type="SYSTEM",
                actor_id="DETECTOR_ENGINE",
                summary=f"SLA breach detected at {event.stage}: latency {event.duration_ms}ms exceeded demo threshold {sla_threshold_ms}ms.",
                metadata={
                    "stage": event.stage,
                    "service": event.service_name,
                    "duration_ms": event.duration_ms,
                    "sla_threshold_ms": sla_threshold_ms,
                    "breach_ms": breach_ms
                }
            )

            # Issue operator alert event to audit trail
            audit_service.log_event(
                db=db,
                correlation_id=order.correlation_id,
                order_id=order.order_id,
                incident_id=incident.incident_id,
                event_type="OPERATOR_ALERT_ISSUED",
                actor_type="SYSTEM",
                actor_id="DETECTOR_ENGINE",
                summary=f"Operator alert issued for {event.stage} SLA breach: elapsed duration {event.duration_ms}ms exceeded demo threshold {sla_threshold_ms}ms (+{breach_ms}ms breach). Order flagged DELAYED. Status: AWAITING_OPERATOR_INVESTIGATION.",
                metadata={
                    "stage": event.stage,
                    "elapsed_duration_ms": event.duration_ms,
                    "sla_threshold_ms": sla_threshold_ms,
                    "breach_ms": breach_ms,
                    "alert_status": "AWAITING_OPERATOR_INVESTIGATION",
                    "action_required": "OPERATOR_REVIEW"
                }
            )

            # State transition: DETECTED -> ANALYZING before RCA processing
            incident.incident_status = "ANALYZING"
            db.commit()
            db.refresh(incident)

            # Generate advisory RCA
            recent_events = [
                {
                    "stage": e.stage,
                    "endpoint": e.endpoint,
                    "http_status": e.http_status,
                    "duration_ms": e.duration_ms,
                    "error_message": e.error_message
                }
                for e in order.events[-5:]
            ]

            rca_data = rca_engine.analyze_incident(
                incident_id=incident.incident_id,
                order_id=order.order_id,
                stage=event.stage,
                service_name=event.service_name,
                failure_type=incident.failure_type,
                recent_events=recent_events,
                error_message=f"Stage duration {event.duration_ms}ms exceeded demo SLA threshold {sla_threshold_ms}ms by {breach_ms}ms."
            )

            rca_id = f"RCA-{uuid.uuid4().hex[:8].upper()}"
            rca_record = RCAReport(
                rca_id=rca_id,
                incident_id=incident.incident_id,
                failure_category=rca_data["failure_category"],
                affected_service=rca_data["affected_service"],
                observed_evidence=json.dumps(rca_data["observed_evidence"]),
                probable_root_cause=rca_data["probable_root_cause"],
                evidence_strength=rca_data["evidence_strength"],
                corroborating_signals_count=rca_data["corroborating_signals_count"],
                recommended_action=rca_data["recommended_action"],
                risk_level=rca_data["risk_level"],
                explanation=rca_data["explanation"],
                model_source=rca_data["model_source"],
                prompt_tokens=rca_data.get("prompt_tokens", 0)
            )
            db.add(rca_record)
            db.commit()

            audit_service.log_event(
                db=db,
                correlation_id=order.correlation_id,
                order_id=order.order_id,
                incident_id=incident.incident_id,
                event_type="RCA_COMPLETED",
                actor_type="AI_AGENT",
                actor_id=rca_data["model_source"],
                summary=f"Advisory RCA completed: Recommended {rca_data['recommended_action']} ({rca_data['evidence_strength']} evidence).",
                metadata=rca_data
            )

            return incident

        return None


detector = FailureDetectionEngine()

