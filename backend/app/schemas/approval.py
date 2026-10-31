from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from backend.app.schemas.order import OrderResponse
from backend.app.schemas.incident import IncidentResponse, RCAReportResponse


class ApprovalDecisionRequest(BaseModel):
    decision: str = Field(..., examples=["APPROVED", "REJECTED"], description="Decision: APPROVED or REJECTED. OVERRIDE is excluded from MVP.")
    operator_id: str = Field(..., examples=["OP-JATAYU-01"])
    operator_name: str = Field(..., examples=["Devin Lead"])
    operator_notes: Optional[str] = Field(default="", examples=["Verified inventory replenishment at alternate hub."])
    selected_action: Optional[str] = Field(default="SUBSTITUTE_SKU_AND_REALLOCATE", examples=["SUBSTITUTE_SKU_AND_REALLOCATE"])
    action_parameters: Optional[Dict[str, Any]] = Field(
        default=None,
        examples=[{"substitute_sku": "SKU-CYBER-500-ALT", "alternate_hub": "HUB-EAST-02"}]
    )


class ApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    approval_id: str
    incident_id: str
    order_id: str
    selected_action: str
    action_parameters: Optional[Dict[str, Any]] = None
    risk_level: str
    decision: str
    operator_id: Optional[str] = None
    operator_name: Optional[str] = None
    operator_notes: Optional[str] = None
    requested_at: datetime
    decided_at: Optional[datetime] = None

    # Contextual associations for pending queue inspection
    order: Optional[OrderResponse] = None
    incident: Optional[IncidentResponse] = None
    rca_report: Optional[RCAReportResponse] = None


class ApprovalDecisionResponse(BaseModel):
    approval_id: str
    incident_id: str
    decision: str
    selected_action: str
    action_parameters: Optional[Dict[str, Any]] = None
    execution_status: str
    verification_passed: bool
    order_status: str
    current_stage: str

