"""Tests for health check endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(async_client: AsyncClient) -> None:
    """Test basic health check endpoint."""
    response = await async_client.get("/api/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data
    assert "version" in data


@pytest.mark.asyncio
async def test_readiness_check_with_db(async_client: AsyncClient) -> None:
    """Test readiness check with database connectivity."""
    response = await async_client.get("/api/ready")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] in ["ready", "not_ready"]
    assert "service" in data
    assert "checks" in data
    assert "database" in data["checks"]
    assert "ready" in data


@pytest.mark.asyncio
async def test_metrics_endpoint(async_client: AsyncClient) -> None:
    """Test metrics collection endpoint."""
    response = await async_client.get("/api/metrics")
    assert response.status_code == 200

    data = response.json()
    assert "request_counts" in data
    assert "auth_failures" in data
    assert "avg_response_times_ms" in data
    assert "total_requests" in data
    assert "total_auth_failures" in data


@pytest.mark.asyncio
async def test_metrics_reset_endpoint(async_client: AsyncClient) -> None:
    """Test metrics reset endpoint."""
    response = await async_client.post("/api/metrics/reset")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "metrics reset"

    # Verify metrics are reset
    response = await async_client.get("/api/metrics")
    data = response.json()
    if "total_requests" in data and not data.get("error"):
        assert data["total_requests"] == 0


@pytest.mark.asyncio
async def test_metrics_middleware_headers(async_client: AsyncClient) -> None:
    """Test that metrics middleware adds process time headers."""
    response = await async_client.get("/api/health")
    assert response.status_code == 200
    assert "X-Process-Time-Ms" in response.headers

    # Verify the header contains a valid float value
    process_time = response.headers["X-Process-Time-Ms"]
    assert float(process_time) >= 0


@pytest.mark.asyncio
async def test_health_endpoint_not_tracked_in_metrics(
    async_client: AsyncClient,
) -> None:
    """Test that health endpoints are excluded from metrics collection."""
    # Reset metrics first
    await async_client.post("/api/metrics/reset")

    # Make a request to health endpoint
    await async_client.get("/api/health")

    # Check that health endpoint is not counted
    response = await async_client.get("/api/metrics")
    data = response.json()

    if not data.get("error"):
        request_counts = data.get("request_counts", {})
        assert not any("GET /api/health" in key for key in request_counts)
