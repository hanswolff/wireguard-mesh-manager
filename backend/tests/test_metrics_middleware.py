"""Tests for metrics middleware."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import Request, Response

from app.middleware.metrics import MetricsMiddleware


@pytest.fixture
def mock_app() -> MagicMock:
    """Create a mock ASGI app."""
    return MagicMock()


@pytest.fixture
def metrics_middleware(mock_app: MagicMock) -> MetricsMiddleware:
    """Create metrics middleware instance."""
    return MetricsMiddleware(mock_app)


@pytest.fixture
def mock_request() -> MagicMock:
    """Create a mock request."""
    request = MagicMock(spec=Request)
    request.method = "GET"
    request.url = MagicMock()
    request.url.path = "/api/test"
    return request


@pytest.fixture
def mock_response() -> MagicMock:
    """Create a mock response."""
    response = MagicMock(spec=Response)
    response.status_code = 200
    response.headers = {}
    return response


@pytest.mark.asyncio
async def test_middleware_tracks_successful_request(
    metrics_middleware: MetricsMiddleware,
    mock_request: MagicMock,
    mock_response: MagicMock,
) -> None:
    """Test that middleware tracks successful requests."""
    call_next = AsyncMock(return_value=mock_response)

    result = await metrics_middleware.dispatch(mock_request, call_next)

    assert result == mock_response
    assert "X-Process-Time-Ms" in result.headers

    # Check metrics were recorded
    metrics = metrics_middleware.get_metrics()
    assert metrics["total_requests"] == 1  # type: ignore[operator]
    assert "GET /api/test" in metrics["request_counts"]  # type: ignore[operator]


@pytest.mark.asyncio
async def test_middleware_tracks_auth_failures(
    metrics_middleware: MetricsMiddleware, mock_request: MagicMock
) -> None:
    """Test that middleware tracks authentication failures."""
    auth_response = MagicMock(spec=Response)
    auth_response.status_code = 401
    auth_response.headers = {}

    call_next = AsyncMock(return_value=auth_response)

    await metrics_middleware.dispatch(mock_request, call_next)

    metrics = metrics_middleware.get_metrics()
    assert metrics["total_auth_failures"] == 1  # type: ignore[operator]
    assert "/api/test" in metrics["auth_failures"]  # type: ignore[operator]


@pytest.mark.asyncio
async def test_middleware_excludes_health_endpoints(
    metrics_middleware: MetricsMiddleware, mock_app: MagicMock
) -> None:
    """Test that health endpoints are excluded from metrics."""
    # Test health endpoint
    health_request = MagicMock(spec=Request)
    health_request.method = "GET"
    health_request.url = MagicMock()
    health_request.url.path = "/api/health"

    health_response = MagicMock(spec=Response)
    health_response.status_code = 200
    health_response.headers = {}

    call_next = AsyncMock(return_value=health_response)

    await metrics_middleware.dispatch(health_request, call_next)

    metrics = metrics_middleware.get_metrics()
    assert metrics["total_requests"] == 0


@pytest.mark.asyncio
async def test_middleware_excludes_metrics_endpoints(
    metrics_middleware: MetricsMiddleware, mock_app: MagicMock
) -> None:
    """Test that metrics endpoints are excluded from tracking."""
    metrics_request = MagicMock(spec=Request)
    metrics_request.method = "GET"
    metrics_request.url = MagicMock()
    metrics_request.url.path = "/api/metrics"

    metrics_response = MagicMock(spec=Response)
    metrics_response.status_code = 200
    metrics_response.headers = {}

    call_next = AsyncMock(return_value=metrics_response)

    await metrics_middleware.dispatch(metrics_request, call_next)

    metrics = metrics_middleware.get_metrics()
    assert metrics["total_requests"] == 0


@pytest.mark.asyncio
async def test_middleware_excludes_ready_endpoints(
    metrics_middleware: MetricsMiddleware, mock_app: MagicMock
) -> None:
    """Test that readiness endpoint is excluded from metrics."""
    ready_request = MagicMock(spec=Request)
    ready_request.method = "GET"
    ready_request.url = MagicMock()
    ready_request.url.path = "/api/ready"

    ready_response = MagicMock(spec=Response)
    ready_response.status_code = 200
    ready_response.headers = {}

    call_next = AsyncMock(return_value=ready_response)

    await metrics_middleware.dispatch(ready_request, call_next)

    metrics = metrics_middleware.get_metrics()
    assert metrics["total_requests"] == 0


def test_should_track_endpoint(metrics_middleware: MetricsMiddleware) -> None:
    """Test the _should_track_endpoint method."""
    assert not metrics_middleware._should_track_endpoint("/api/health")
    assert not metrics_middleware._should_track_endpoint("/api/health/detailed")
    assert not metrics_middleware._should_track_endpoint("/api/ready")
    assert not metrics_middleware._should_track_endpoint("/api/metrics")
    assert not metrics_middleware._should_track_endpoint("/api/metrics/reset")
    assert metrics_middleware._should_track_endpoint("/api/devices")
    assert metrics_middleware._should_track_endpoint("/api/networks/1")


def test_reset_metrics(metrics_middleware: MetricsMiddleware) -> None:
    """Test metrics reset functionality."""
    # Add some test data
    metrics_middleware.request_metrics[("GET", "/api/test")] = {
        "count": 5,
        "total_time": 100.0,
    }
    metrics_middleware.auth_failure_counts["/api/auth"] = 2

    # Reset metrics
    metrics_middleware.reset_metrics()

    # Verify metrics are cleared
    metrics = metrics_middleware.get_metrics()
    assert metrics["total_requests"] == 0  # type: ignore[operator]
    assert metrics["total_auth_failures"] == 0  # type: ignore[operator]
    assert len(metrics["request_counts"]) == 0  # type: ignore[arg-type]
    assert len(metrics["auth_failures"]) == 0  # type: ignore[arg-type]


def test_average_response_time_calculation(
    metrics_middleware: MetricsMiddleware,
) -> None:
    """Test average response time calculation."""
    # Add test data: 3 requests with total time 300ms
    metrics_middleware.request_metrics[("GET", "/api/test")] = {
        "count": 3,
        "total_time": 300.0,
    }

    metrics = metrics_middleware.get_metrics()
    avg_time = metrics["avg_response_times_ms"]["GET /api/test"]  # type: ignore[index]
    assert avg_time == 100.0  # 300ms / 3 requests = 100ms average


def test_average_response_time_zero_requests(
    metrics_middleware: MetricsMiddleware,
) -> None:
    """Test average response time with zero requests."""
    # Add test data with zero requests
    metrics_middleware.request_metrics[("GET", "/api/test")] = {
        "count": 0,
        "total_time": 0.0,
    }

    metrics = metrics_middleware.get_metrics()
    avg_time = metrics["avg_response_times_ms"]["GET /api/test"]  # type: ignore[index]
    assert avg_time == 0.0
