from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from backend.app.db.session import get_db
from backend.app.models.order import Order, Incident, OperatorApproval
from backend.app.schemas.common import ApiResponse
from backend.app.schemas.analytics import (
    AnalyticsMetricsData,
    FailureCategoryCount,
    FailureDistributionData,
)

router = APIRouter()


@router.get(
    "/analytics/metrics",
    response_model=ApiResponse[AnalyticsMetricsData],
    summary="Get System Summary Metrics",
    description="Returns aggregate KPI counts across orders and pending approvals."
)
def get_analytics_metrics(db: Session = Depends(get_db)):
    total_orders = db.query(func.count(Order.order_id)).scalar() or 0
    completed_orders = db.query(func.count(Order.order_id)).filter(Order.order_status == "COMPLETED").scalar() or 0
    failed_orders = db.query(func.count(Order.order_id)).filter(Order.order_status == "FAILED").scalar() or 0
    delayed_orders = db.query(func.count(Order.order_id)).filter(Order.order_status == "DELAYED").scalar() or 0
    in_progress_orders = db.query(func.count(Order.order_id)).filter(
        Order.order_status.in_(["PENDING", "PROCESSING"])
    ).scalar() or 0

    pending_approvals = db.query(func.count(OperatorApproval.approval_id)).filter(
        OperatorApproval.decision == "PENDING"
    ).scalar() or 0

    data = AnalyticsMetricsData(
        total_orders=total_orders,
        completed_orders=completed_orders,
        failed_orders=failed_orders,
        delayed_orders=delayed_orders,
        pending_approvals=pending_approvals,
        in_progress_orders=in_progress_orders
    )
    return ApiResponse(success=True, data=data, message="Summary metrics retrieved successfully")


@router.get(
    "/analytics/distribution",
    response_model=ApiResponse[FailureDistributionData],
    summary="Get Failure Category Distribution",
    description="Returns aggregate incident counts grouped by failure category for visualization."
)
def get_failure_distribution(db: Session = Depends(get_db)):
    rows = (
        db.query(Incident.failure_category, func.count(Incident.incident_id))
        .group_by(Incident.failure_category)
        .all()
    )

    categories = [
        FailureCategoryCount(category=category or "UNKNOWN", count=count)
        for category, count in rows
    ]
    total_incidents = sum(item.count for item in categories)
    distribution_map = {item.category: item.count for item in categories}

    data = FailureDistributionData(
        categories=categories,
        total_incidents=total_incidents,
        distribution_map=distribution_map
    )
    return ApiResponse(success=True, data=data, message="Failure distribution retrieved successfully")

