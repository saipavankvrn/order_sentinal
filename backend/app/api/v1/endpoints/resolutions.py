from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from backend.app.db.session import get_db
from backend.app.schemas.resolution import ResolutionExecuteRequest, ResolutionActionResponse
from backend.app.schemas.common import ApiResponse
from backend.app.services.resolution_service import resolution_service
from backend.app.services.order_service import order_service

router = APIRouter()


@router.post(
    "/resolutions/execute",
    response_model=ApiResponse[ResolutionActionResponse],
    summary="Execute Resolution Action",
    description="Dispatches policy-authorized recovery retry with database idempotency and state verification."
)
def execute_resolution(
    request: ResolutionExecuteRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    action = resolution_service.execute_resolution(
        db=db,
        incident_id=request.incident_id,
        action_type=request.action_type,
        idempotency_key=request.idempotency_key
    )

    # Schedule decoupled background execution for remaining journey stages post-response.
    # Guard: Do NOT schedule duplicate continuation on idempotency replay.
    if (
        action.verification_passed
        and action.execution_status == "SUCCEEDED"
        and not getattr(action, "_is_idempotent_replay", False)
    ):
        background_tasks.add_task(order_service.resume_remaining_stages_background, action.order_id)

    # Fetch updated order status (authentically PROCESSING in database at this recovery milestone)
    order_status = action.incident.order.order_status if action.incident and action.incident.order else "PROCESSING"

    data = ResolutionActionResponse(
        action_id=action.action_id,
        incident_id=action.incident_id,
        order_id=action.order_id,
        action_type=action.action_type,
        attempt_number=action.attempt_number,
        backoff_delay_sec=action.backoff_delay_sec,
        execution_status=action.execution_status,
        verification_passed=action.verification_passed,
        verification_details=action.verification_details,
        order_status=order_status,
        completed_at=action.completed_at
    )

    msg = (
        "Resolution retry executed and downstream state verified successfully."
        if action.verification_passed
        else "Resolution retry executed but downstream state verification did not pass."
    )

    return ApiResponse(
        success=action.verification_passed,
        data=data,
        message=msg
    )

