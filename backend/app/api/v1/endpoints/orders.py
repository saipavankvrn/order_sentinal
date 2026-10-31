from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.app.db.session import get_db
from backend.app.models.order import Order
from backend.app.schemas.order import OrderCreate, OrderResponse, OrderListResponse, OrderJourneyResponse
from backend.app.schemas.common import ApiResponse, current_utc_iso
from backend.app.services.order_service import order_service

router = APIRouter()


@router.get(
    "/orders",
    response_model=ApiResponse[OrderListResponse],
    summary="List Monitored Orders",
    description="Returns paginated orders with optional status or customer search filters."
)
def list_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    skip: Optional[int] = Query(None, ge=0, description="Offset for pagination (overrides page if provided)"),
    status: Optional[str] = Query(None, description="Filter by order_status"),
    search: Optional[str] = Query(None, description="Search by order_id or customer_name"),
    is_demo: Optional[bool] = Query(None, description="Filter by live demonstration order flag"),
    demo_session_id: Optional[str] = Query(None, description="Filter by specific demo session identifier"),
    db: Session = Depends(get_db)
):
    query = db.query(Order)
    if is_demo is True:
        query = query.filter(Order.is_demo_order == True)
    elif is_demo is False:
        query = query.filter((Order.is_demo_order == False) | (Order.is_demo_order == None))

    if demo_session_id:
        query = query.filter(Order.demo_session_id == demo_session_id)

    if status:
        query = query.filter(Order.order_status == status)
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Order.order_id.ilike(search_filter)) |
            (Order.customer_name.ilike(search_filter)) |
            (Order.product_name.ilike(search_filter))
        )

    total = query.count()
    if skip is not None:
        offset = skip
        page = (skip // limit) + 1
    else:
        offset = (page - 1) * limit

    orders = query.order_by(Order.created_at.desc()).offset(offset).limit(limit).all()

    data = OrderListResponse(
        total=total,
        page=page,
        limit=limit,
        skip=offset,
        items=[OrderResponse.model_validate(o) for o in orders]
    )
    return ApiResponse(success=True, data=data, message="Orders retrieved successfully")


@router.post(
    "/orders",
    response_model=ApiResponse[OrderResponse],
    status_code=201,
    summary="Create Synthetic Order",
    description="Creates a new synthetic order record with PENDING status."
)
def create_order(
    order_in: OrderCreate,
    db: Session = Depends(get_db)
):
    order = order_service.create_order(db, order_in)
    return ApiResponse(
        success=True,
        data=OrderResponse.model_validate(order),
        message="Synthetic order created successfully"
    )


@router.get(
    "/orders/{order_id}",
    response_model=ApiResponse[OrderResponse],
    summary="Get Order Details",
    description="Retrieves a single order by its unique ID."
)
def get_order(
    order_id: str,
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter_by(order_id=order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail=f"Order '{order_id}' not found.")
    return ApiResponse(
        success=True,
        data=OrderResponse.model_validate(order),
        message="Order retrieved successfully"
    )


@router.get(
    "/orders/{order_id}/journey",
    response_model=ApiResponse[OrderJourneyResponse],
    summary="Get Order Journey Timeline",
    description="Returns the 7-stage chronological timeline and raw telemetry events for an order."
)
def get_order_journey(
    order_id: str,
    db: Session = Depends(get_db)
):
    journey = order_service.get_order_journey(db, order_id)
    if not journey:
        raise HTTPException(status_code=404, detail=f"Order journey for '{order_id}' not found.")
    return ApiResponse(
        success=True,
        data=journey,
        message="Order journey timeline retrieved successfully"
    )

