from pydantic import BaseModel
from typing import List, Dict, Any


class AnalyticsMetricsData(BaseModel):
    total_orders: int
    completed_orders: int
    failed_orders: int
    delayed_orders: int
    pending_approvals: int
    in_progress_orders: int


class FailureCategoryCount(BaseModel):
    category: str
    count: int


class FailureDistributionData(BaseModel):
    categories: List[FailureCategoryCount]
    total_incidents: int
    distribution_map: Dict[str, int]

