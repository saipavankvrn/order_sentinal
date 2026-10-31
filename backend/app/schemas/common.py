from typing import Generic, TypeVar, Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


def current_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ApiResponse(BaseModel, Generic[DataT]):
    success: bool = True
    data: DataT
    message: str = "Operation completed successfully"
    timestamp: str = Field(default_factory=current_utc_iso)


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None


class ApiErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail
    timestamp: str = Field(default_factory=current_utc_iso)

