import time
from fastapi import APIRouter
from pydantic import BaseModel
from backend.app.core.config import settings
from backend.app.db.session import verify_database_connection
from backend.app.schemas.common import ApiResponse, current_utc_iso

router = APIRouter()
START_TIME = time.time()


class DatabaseHealth(BaseModel):
    status: str
    engine: str
    wal_mode: bool


class AiEngineHealth(BaseModel):
    gemini_available: bool
    model_configured: str
    fallback_mode: bool


class HealthData(BaseModel):
    status: str
    database: DatabaseHealth
    ai_engine: AiEngineHealth
    uptime_seconds: int


@router.get(
    "/health",
    response_model=ApiResponse[HealthData],
    summary="System Health & Diagnostics Check",
    description="Verifies SQLite connectivity and reports AI engine fallback readiness."
)
def get_health() -> ApiResponse[HealthData]:
    db_info = verify_database_connection()
    db_connected = db_info.get("status") == "CONNECTED"

    has_gemini_key = bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip())

    health_status = "HEALTHY" if db_connected else "DEGRADED"

    data = HealthData(
        status=health_status,
        database=DatabaseHealth(
            status=db_info.get("status", "UNKNOWN"),
            engine=db_info.get("engine", "sqlite"),
            wal_mode=db_info.get("wal_mode", False)
        ),
        ai_engine=AiEngineHealth(
            gemini_available=has_gemini_key,
            model_configured=settings.GEMINI_MODEL_ID,
            fallback_mode=not has_gemini_key
        ),
        uptime_seconds=int(time.time() - START_TIME)
    )

    return ApiResponse(
        success=db_connected,
        data=data,
        message="System is healthy and operational" if db_connected else "Database connectivity issue detected",
        timestamp=current_utc_iso()
    )

