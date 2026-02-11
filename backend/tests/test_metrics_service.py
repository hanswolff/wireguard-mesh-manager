"""Tests for metrics service."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.services.metrics import MetricsService


@pytest.fixture
def mock_middleware() -> MagicMock:
    """Create a mock metrics middleware."""
    middleware = MagicMock()
    middleware.get_metrics.return_value = {
        "request_counts": {"GET /api/test": 5},
        "auth_failures": {"/api/auth": 2},
        "avg_response_times_ms": {"GET /api/test": 100.5},
        "total_requests": 5,
        "total_auth_failures": 2,
    }
    return middleware


@pytest.fixture
def metrics_service(mock_middleware: MagicMock) -> MetricsService:
    """Create metrics service with mock middleware."""
    return MetricsService(mock_middleware)


def test_get_metrics_with_middleware(metrics_service: MetricsService) -> None:
    """Test getting metrics when middleware is available."""
    metrics = metrics_service.get_metrics()

    assert metrics["total_requests"] == 5
    assert metrics["total_auth_failures"] == 2
    assert "GET /api/test" in metrics["request_counts"]
    assert "/api/auth" in metrics["auth_failures"]


def test_get_metrics_without_middleware() -> None:
    """Test getting metrics when middleware is not available."""
    service = MetricsService(None)
    metrics = service.get_metrics()

    assert "error" in metrics
    assert metrics["error"] == "Metrics not available"


def test_reset_metrics_with_middleware(metrics_service: MetricsService) -> None:
    """Test resetting metrics when middleware is available."""
    result = metrics_service.reset_metrics()

    assert result["status"] == "metrics reset"
    metrics_service.metrics_middleware.reset_metrics.assert_called_once()


def test_reset_metrics_without_middleware() -> None:
    """Test resetting metrics when middleware is not available."""
    service = MetricsService(None)
    result = service.reset_metrics()

    assert "error" in result
    assert result["error"] == "Metrics not available"
