from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class RCAReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rca_id: str
    incident_id: str
    failure_category: str
    affected_service: str
    observed_evidence: List[str]
    probable_root_cause: str
    evidence_strength: str  # HIGH, MEDIUM, LOW
    corroborating_signals_count: int
    recommended_action: str
    risk_level: str
    explanation: str
    model_source: str
    prompt_tokens: int
    created_at: datetime


class IncidentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    incident_id: str
    order_id: str
    stage: str
    service_name: str
    failure_category: str
    failure_type: str
    incident_status: str
    severity: str
    retry_count: int
    max_retries: int
    detected_at: datetime
    resolved_at: Optional[datetime] = None


class IncidentDetailResponse(BaseModel):
    incident: IncidentResponse
    rca_report: Optional[RCAReportResponse] = None
    order_id: str
    correlation_id: str
