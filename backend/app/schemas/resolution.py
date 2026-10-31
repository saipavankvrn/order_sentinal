from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class ResolutionExecuteRequest(BaseModel):
    incident_id: str = Field(..., examples=["INC-2026-1001"])
    action_type: str = Field(default="RETRY_WITH_BACKOFF", examples=["RETRY_WITH_BACKOFF"])
    idempotency_key: str = Field(..., examples=["idemp_ORD-2026-1001_INVENTORY_1"])


class ResolutionActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    action_id: str
    incident_id: str
    order_id: str
    action_type: str
    attempt_number: int
    backoff_delay_sec: int
    execution_status: str
    verification_passed: bool
    verification_details: Optional[str] = None
    order_status: str
    completed_at: Optional[datetime] = None
