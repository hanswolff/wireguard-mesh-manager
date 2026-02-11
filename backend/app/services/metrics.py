"""Service for collecting and exposing application metrics."""

from __future__ import annotations

from typing import Any


class MetricsService:
    """Service for managing application metrics."""

    def __init__(self, metrics_middleware: Any) -> None:
        """Initialize metrics service with middleware instance."""
        self.metrics_middleware = metrics_middleware

    def get_metrics(self) -> dict[str, Any]:
        """Get current application metrics."""
        if not self.metrics_middleware:
            return {"error": "Metrics not available"}
        return self.metrics_middleware.get_metrics()

    def reset_metrics(self) -> dict[str, str]:
        """Reset all metrics."""
        if not self.metrics_middleware:
            return {"error": "Metrics not available"}
        self.metrics_middleware.reset_metrics()
        return {"status": "metrics reset"}
