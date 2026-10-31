from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    log_id: int
    correlation_id: str
    order_id: Optional[str] = None
    incident_id: Optional[str] = None
    event_type: str
    actor_type: str
    actor_id: str
    summary: str
    metadata_json: Optional[str] = None
    timestamp: datetime
