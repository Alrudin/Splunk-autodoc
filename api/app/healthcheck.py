"""Health check endpoints for monitoring and load balancer probes."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
@router.get("/healthz")
async def health_check() -> dict[str, str]:
    """
    Simple health check endpoint.

    Returns:
        Status message indicating service is running
    """
    return {"status": "healthy"}


@router.get("/readyz")
async def readiness_check() -> dict[str, str]:
    """
    Readiness check endpoint for load balancer probes.

    In a full implementation, this would verify:
    - Database connectivity
    - Storage accessibility
    - Required services availability

    Returns:
        Status message indicating service is ready
    """
    # TODO: Add actual checks for database, storage, etc.
    return {"status": "ready"}
