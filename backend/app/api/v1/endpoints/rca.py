import json
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.db.session import get_db
from backend.app.models.order import Incident, RCAReport
from backend.app.schemas.incident import RCAReportResponse
from backend.app.schemas.common import ApiResponse
from backend.app.ai.gemini_rca import rca_engine
from backend.app.services.audit_service import audit_service

router = APIRouter()


@router.post(
    "/rca/{incident_id}/analyze",
    response_model=ApiResponse[RCAReportResponse],
    summary="Generate or Retrieve Advisory RCA Report",
    description="Generates an advisory root cause analysis via Gemini API or deterministic fallback."
)
def analyze_incident_rca(
    incident_id: str,
    db: Session = Depends(get_db)
):
    incident = db.query(Incident).filter_by(incident_id=incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found.")

    if incident.rca_report:
        rca = incident.rca_report
        evidence_list = json.loads(rca.observed_evidence) if rca.observed_evidence else []
        data = RCAReportResponse(
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
        return ApiResponse(success=True, data=data, message="Existing advisory RCA retrieved.")

    # Generate new RCA
    order = incident.order
    recent_events = [
        {
            "stage": e.stage,
            "endpoint": e.endpoint,
            "http_status": e.http_status,
            "duration_ms": e.duration_ms,
            "error_message": e.error_message
        }
        for e in order.events[-5:]
    ] if order else []

    rca_data = rca_engine.analyze_incident(
        incident_id=incident.incident_id,
        order_id=incident.order_id,
        stage=incident.stage,
        service_name=incident.service_name,
        failure_type=incident.failure_type,
        recent_events=recent_events,
        error_message=""
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
    db.refresh(rca_record)

    if order:
        audit_service.log_event(
            db=db,
            correlation_id=order.correlation_id,
            order_id=order.order_id,
            incident_id=incident.incident_id,
            event_type="RCA_COMPLETED",
            actor_type="AI_AGENT",
            actor_id=rca_data["model_source"],
            summary=f"Advisory RCA generated: {rca_data['recommended_action']}.",
            metadata=rca_data
        )

    data = RCAReportResponse(
        rca_id=rca_record.rca_id,
        incident_id=rca_record.incident_id,
        failure_category=rca_record.failure_category,
        affected_service=rca_record.affected_service,
        observed_evidence=rca_data["observed_evidence"],
        probable_root_cause=rca_record.probable_root_cause,
        evidence_strength=rca_record.evidence_strength,
        corroborating_signals_count=rca_record.corroborating_signals_count,
        recommended_action=rca_record.recommended_action,
        risk_level=rca_record.risk_level,
        explanation=rca_record.explanation,
        model_source=rca_record.model_source,
        prompt_tokens=rca_record.prompt_tokens,
        created_at=rca_record.created_at
    )
    return ApiResponse(success=True, data=data, message="Advisory RCA generated successfully.")

