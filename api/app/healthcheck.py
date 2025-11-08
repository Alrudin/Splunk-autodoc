"""Health check endpoints."""


from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import check_db_connection, get_db

# Create router for health check endpoints
healthcheck_router = APIRouter(tags=["health"])

@healthcheck_router.get("/healthz")
def healthz(db: Session | None = None) -> dict | Response:

    """
    Health check endpoint for container and Kubernetes probes.

    Verifies database connectivity by executing a simple query.
    Returns 200 OK if healthy, 503 Service Unavailable if unhealthy.
    """
    if db is None:
        db = Depends(get_db)

    if check_db_connection():
        return {
            "status": "healthy",
            "database": "connected"
        }
    else:
        return Response(
            content='{"status": "unhealthy", "database": "disconnected"}',
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            media_type="application/json"
        )
