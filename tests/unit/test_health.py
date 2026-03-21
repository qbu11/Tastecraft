"""Health endpoint tests."""

import pytest
from httpx import AsyncClient


@pytest.mark.unit
async def test_health_check(client: AsyncClient) -> None:
    """Health endpoint returns healthy status."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "crew-media-ops"


@pytest.mark.unit
async def test_readiness_check(client: AsyncClient) -> None:
    """Readiness endpoint returns ready status."""
    response = await client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
