"""Health check routes."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Check API health status."""
    return {"status": "healthy", "service": "crew-media-ops"}


@router.get("/ready")
async def readiness_check() -> dict[str, str]:
    """Check if service is ready to accept requests."""
    return {"status": "ready"}
