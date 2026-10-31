from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class OrderCreate(BaseModel):
    customer_name: str = Field(..., examples=["Sarah Connor"])
    customer_email: str = Field(..., examples=["sarah.connor@example.com"])
    product_sku: str = Field(..., examples=["SKU-CYBER-500"])
    product_name: str = Field(..., examples=["High-Performance Fiber Gateway"])
    order_amount: float = Field(..., gt=0, examples=[199.99])
    currency: str = Field(default="USD", examples=["USD"])
    is_demo_order: Optional[bool] = Field(default=False, description="Flag indicating live demo order")
    demo_session_id: Optional[str] = Field(default=None, description="Active demo session identifier")


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order_id: str
    correlation_id: str
    customer_id: str
    customer_name: str
    customer_email: str
    product_sku: str
    product_name: str
    order_amount: float
    currency: str
    current_stage: str
    order_status: str
    payment_status: str
    inventory_status: str
    fulfilment_status: str
    is_demo_order: Optional[bool] = False
    demo_session_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class OrderEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: str
    order_id: str
    correlation_id: str
    stage: str
    service_name: str
    endpoint: str
    http_method: str
    http_status: int
    duration_ms: int
    event_status: str
    payload_summary: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    timestamp: datetime


class JourneyStageSummary(BaseModel):
    stage_name: str
    status: str
    duration_ms: int
    http_status: Optional[int] = None
    timestamp: datetime
    error_message: Optional[str] = None


class OrderJourneyResponse(BaseModel):
    order_id: str
    correlation_id: str
    current_stage: str
    order_status: str
    stages: List[JourneyStageSummary]
    raw_events: List[OrderEventResponse]


class OrderListResponse(BaseModel):
    total: int
    page: int
    limit: int
    skip: Optional[int] = None
    items: List[OrderResponse]
