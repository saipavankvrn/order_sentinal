import json
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.app.db.session import get_db
from backend.app.models.order import Incident
from backend.app.schemas.incident import IncidentResponse, IncidentDetailResponse, RCAReportResponse
from backend.app.schemas.common import ApiResponse

router = APIRouter()


@router.get(
    "/incidents",
    response_model=ApiResponse[List[IncidentResponse]],
    summary="List Incidents",
    description="Returns detected failure incidents with optional status or category filters."
)
def list_incidents(
    order_id: Optional[str] = Query(None, description="Filter by order_id"),
    status: Optional[str] = Query(None, description="Filter by incident_status"),
    category: Optional[str] = Query(None, description="Filter by failure_category"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(Incident)
    if order_id:
        query = query.filter(Incident.order_id == order_id)
    if status:
        query = query.filter(Incident.incident_status == status)
    if category:
        query = query.filter(Incident.failure_category == category)
    if severity:
        query = query.filter(Incident.severity == severity)

    incidents = query.order_by(Incident.detected_at.desc()).limit(limit).all()
    return ApiResponse(
        success=True,
        data=[IncidentResponse.model_validate(i) for i in incidents],
        message="Incidents retrieved successfully"
    )


@router.get(
    "/incidents/{incident_id}",
    response_model=ApiResponse[IncidentDetailResponse],
    summary="Get Incident Detail",
    description="Returns detailed incident record including advisory RCA diagnosis."
)
def get_incident(
    incident_id: str,
    db: Session = Depends(get_db)
):
    incident = db.query(Incident).filter_by(incident_id=incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found.")

    rca_resp = None
    if incident.rca_report:
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

    data = IncidentDetailResponse(
        incident=IncidentResponse.model_validate(incident),
        rca_report=rca_resp,
        order_id=incident.order_id,
        correlation_id=incident.order.correlation_id if incident.order else ""
    )
    return ApiResponse(
        success=True,
        data=data,
        message="Incident details retrieved successfully"
    )

