from typing import List, Optional
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from backend.app.db.session import get_db
from backend.app.schemas.approval import ApprovalDecisionRequest, ApprovalResponse, ApprovalDecisionResponse
from backend.app.schemas.common import ApiResponse
from backend.app.services.approval_service import approval_service

router = APIRouter()


@router.get(
    "/approvals/pending",
    response_model=ApiResponse[List[ApprovalResponse]],
    summary="List Pending Approvals",
    description="Returns array of incidents and approval requests currently awaiting human operator decision."
)
def list_pending_approvals(
    demo_session_id: Optional[str] = None,
    is_demo: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    approvals = approval_service.list_pending_approvals(db, demo_session_id=demo_session_id, is_demo=is_demo)
    return ApiResponse(
        success=True,
        data=approvals,
        message=f"Retrieved {len(approvals)} pending approval request(s)."
    )


@router.get(
    "/approvals/{approval_id}",
    response_model=ApiResponse[ApprovalResponse],
    summary="Get Approval Detail",
    description="Returns full approval record including linked order, incident, and advisory RCA details."
)
def get_approval(approval_id: str, db: Session = Depends(get_db)):
    approval = approval_service.get_approval(db, approval_id)
    return ApiResponse(
        success=True,
        data=approval,
        message="Approval record retrieved successfully."
    )


@router.post(
    "/approvals/{approval_id}/decide",
    response_model=ApiResponse[ApprovalDecisionResponse],
    summary="Submit Operator Decision",
    description="Processes operator decision (APPROVED or REJECTED) with parameter validation and verified state execution."
)
def submit_decision(
    approval_id: str,
    request: ApprovalDecisionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    data, message = approval_service.submit_decision(
        db=db,
        approval_id=approval_id,
        request=request,
        background_tasks=background_tasks
    )
    return ApiResponse(
        success=data.verification_passed if data.decision == "APPROVED" else True,
        data=data,
        message=message
    )

