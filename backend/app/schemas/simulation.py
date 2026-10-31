from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from backend.app.schemas.order import OrderResponse, OrderEventResponse
from backend.app.schemas.incident import IncidentResponse, RCAReportResponse
from backend.app.schemas.resolution import ResolutionActionResponse
from backend.app.schemas.approval import ApprovalResponse


class SimulationTriggerRequest(BaseModel):
    scenario_key: str = Field(
        ...,
        examples=["SCENARIO_1_HTTP_503_SELF_HEAL", "SCENARIO_2_SLA_DELAY", "SCENARIO_3_HARD_REJECTION", "SCENARIO_0_CLEAN_RUN", "RANDOM"],
        description="Scenario code: SCENARIO_1_HTTP_503_SELF_HEAL, SCENARIO_2_SLA_DELAY, SCENARIO_3_HARD_REJECTION, SCENARIO_0_CLEAN_RUN, or RANDOM"
    )
    order_id: Optional[str] = Field(default=None, examples=["ORD-LIVE-1A2B3C4D"])
    customer_name: Optional[str] = Field(default="Sarah Connor", examples=["Sarah Connor"])
    customer_email: Optional[str] = Field(default="sarah.connor@example.com", examples=["sarah.connor@example.com"])
    product_sku: Optional[str] = Field(default="SKU-CYBER-500", examples=["SKU-CYBER-500"])
    product_name: Optional[str] = Field(default="High-Performance Fiber Gateway", examples=["High-Performance Fiber Gateway"])
    order_amount: Optional[float] = Field(default=199.99, examples=[199.99])
    auto_resolve: Optional[bool] = Field(
        default=False,
        description="If True, automatically executes policy retry and verified self-healing immediately."
    )
    is_demo_order: Optional[bool] = Field(default=True, description="Marks order as part of demonstration")
    demo_session_id: Optional[str] = Field(default=None, description="Active demonstration session identifier")
    random_seed: Optional[int] = Field(default=None, description="Seed for deterministic testing of RANDOM mode")
    random_outcome_override: Optional[str] = Field(
        default=None,
        description="Override outcome for test verification: SUCCESS, HTTP_503, SLA_DELAY, OUT_OF_STOCK"
    )


class SimulationScenarioResponse(BaseModel):
    scenario_key: str
    order: OrderResponse
    incident: Optional[IncidentResponse] = None
    rca: Optional[RCAReportResponse] = None
    resolution: Optional[ResolutionActionResponse] = None
    approval: Optional[ApprovalResponse] = None
    events: List[OrderEventResponse] = []
    operator_alert: Optional[Dict[str, Any]] = None
    message: str
    selected_outcome: Optional[str] = None
    outcome_reason: Optional[str] = None
    demo_probabilities: Optional[Dict[str, float]] = None


class DemoSessionResetRequest(BaseModel):
    demo_session_id: str = Field(..., description="Unique demo session identifier to purge")


class DemoSessionResetResponse(BaseModel):
    demo_session_id: str
    cleared_orders_count: int
    message: str
