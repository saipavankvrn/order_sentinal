import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.db.session import verify_database_connection, init_db
from backend.app.api.v1.router import api_v1_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup validation & database initialization
    logger.info(f"Starting {settings.APP_NAME} in [{settings.APP_ENV}] mode...")
    init_db()

    db_status = verify_database_connection()
    logger.info(f"Database connectivity check: {db_status}")

    if settings.GEMINI_API_KEY:
        logger.info(f"Gemini API configured with model: {settings.GEMINI_MODEL_ID}")
    else:
        logger.info("Gemini API key not found. Deterministic RCA fallback engine active.")

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME}...")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.2.1",
    description="OrderFlow Sentinel — AI-Powered Self-Healing Order Failure Detection and Resolution Platform",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API V1 routes
app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

# Static files & Dashboard UI
_static_dir = os.path.join(os.path.dirname(__file__), "static")
_frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))

if not os.path.exists(_static_dir):
    os.makedirs(_static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=_static_dir), name="static")

if os.path.exists(_frontend_dist):
    _assets_dir = os.path.join(_frontend_dist, "assets")
    if os.path.exists(_assets_dir):
        app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")
    _ui_dir = _frontend_dist
else:
    _ui_dir = _static_dir


@app.get("/ui", response_class=HTMLResponse, tags=["Dashboard UI"])
def read_dashboard_ui():
    """Serves the OrderFlow Sentinel operator monitoring & simulation dashboard."""
    index_file = os.path.join(_ui_dir, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>OrderFlow Sentinel Dashboard UI</h1><p>UI template loading...</p>")


@app.get("/", tags=["Root"])
def read_root():
    return {
        "name": settings.APP_NAME,
        "version": "1.2.1",
        "status": "ONLINE",
        "docs": "/docs",
        "health": f"{settings.API_V1_PREFIX}/health",
        "ui": "/ui"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
