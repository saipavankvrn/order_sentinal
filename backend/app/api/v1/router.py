from fastapi import APIRouter
from backend.app.api.v1.endpoints import (
    health,
    orders,
    incidents,
    rca,
    resolutions,
    simulation,
    audit,
    approvals,
    analytics,
)

api_v1_router = APIRouter()

# Mount all V1 domain routers
api_v1_router.include_router(health.router, tags=["Health & Diagnostics"])
api_v1_router.include_router(orders.router, tags=["Order Management"])
api_v1_router.include_router(incidents.router, tags=["Incidents"])
api_v1_router.include_router(rca.router, tags=["Advisory RCA"])
api_v1_router.include_router(resolutions.router, tags=["Resolutions"])
api_v1_router.include_router(approvals.router, tags=["Human Approvals"])
api_v1_router.include_router(simulation.router, tags=["Simulation Controls"])
api_v1_router.include_router(audit.router, tags=["Audit Trail"])
api_v1_router.include_router(analytics.router, tags=["Dashboard & Analytics"])
