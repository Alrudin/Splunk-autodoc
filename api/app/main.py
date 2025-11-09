from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings  # type: ignore
from app.database import init_db  # type: ignore
from app.healthcheck import router as healthcheck_router  # type: ignore
from app.routers.graphs import router as graphs_router  # type: ignore
from app.routers.jobs import router as jobs_router  # type: ignore
from app.routers.projects import router as projects_router  # type: ignore
from app.routers.uploads import router as uploads_router  # type: ignore

# Initialize FastAPI application
app = FastAPI(
    title="Splunk Event Flow Graph API",
    version="2.0.0",
    description=(
        "Backend API for Splunk Event Flow Graph - "
        "automated documentation generation for Splunk configurations"
    ),
    docs_url="/docs",
    openapi_url="/openapi.json",
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(healthcheck_router)
app.include_router(projects_router, prefix="/api/v1")
app.include_router(uploads_router, prefix="/api/v1")
app.include_router(jobs_router, prefix="/api/v1")
app.include_router(graphs_router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize database on application startup (for development)."""
    init_db()


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint providing basic API information."""
    return {
        "name": "Splunk Event Flow Graph API",
        "version": "2.0.0",
        "docs_url": "/docs",
        "health_check": "/health",
    }
