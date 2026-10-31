from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.app.db.session import get_db
from backend.app.schemas.audit import AuditLogResponse
from backend.app.schemas.common import ApiResponse
from backend.app.services.audit_service import audit_service

router = APIRouter()


@router.get(
    "/audit",
    response_model=ApiResponse[List[AuditLogResponse]],
    summary="Query Audit Logs",
    description="Returns application-level append-only audit records. Records cannot be modified or deleted via the API."
)
def get_audit_logs(
    order_id: Optional[str] = Query(None, description="Filter by order_id"),
    incident_id: Optional[str] = Query(None, description="Filter by incident_id"),
    actor_type: Optional[str] = Query(None, description="Filter by actor_type (SYSTEM, AI_AGENT, OPERATOR, SIMULATOR)"),
    limit: int = Query(50, ge=1, le=100),
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db)
):
    logs = audit_service.get_logs(
        db=db,
        order_id=order_id,
        incident_id=incident_id,
        actor_type=actor_type,
        limit=limit,
        page=page
    )
    return ApiResponse(
        success=True,
        data=[AuditLogResponse.model_validate(l) for l in logs],
        message="Audit logs retrieved successfully"
    )

