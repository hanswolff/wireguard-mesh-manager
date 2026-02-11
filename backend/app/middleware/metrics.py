"""Metrics collection middleware for monitoring API usage."""

from __future__ import annotations

import time
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from starlette.middleware.base import BaseHTTPMiddleware

if TYPE_CHECKING:
    from fastapi import Request, Response


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect basic request metrics."""

    def __init__(self, app: Any) -> None:
        super().__init__(app)
        self.request_metrics: defaultdict[tuple[str, str], dict] = defaultdict(
            lambda: {"count": 0, "total_time": 0.0}
        )
        self.auth_failure_counts: defaultdict[str, int] = defaultdict(int)

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """Process request and collect metrics."""
        start_time = time.time()
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000

        path = request.url.path
        if self._should_track_endpoint(path):
            method_path = (request.method, path)
            self.request_metrics[method_path]["count"] += 1
            self.request_metrics[method_path]["total_time"] += process_time

        if response.status_code in (401, 403):
            self.auth_failure_counts[path] += 1

        response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"
        return response

    def _should_track_endpoint(self, path: str) -> bool:
        """Check if endpoint should be tracked for metrics."""
        excluded_prefixes = (
            "/health",
            "/ready",
            "/metrics",
            "/api/health",
            "/api/ready",
            "/api/metrics",
        )
        return not any(path.startswith(prefix) for prefix in excluded_prefixes)

    def get_metrics(self) -> dict[str, str | int | float | dict]:
        """Get collected metrics."""
        request_counts = {}
        avg_response_times = {}

        for (method, path), metrics in self.request_metrics.items():
            endpoint_key = f"{method} {path}"
            count = metrics["count"]
            total_time = metrics["total_time"]

            request_counts[endpoint_key] = count
            avg_response_times[endpoint_key] = (
                round(total_time / count, 2) if count > 0 else 0
            )

        return {
            "request_counts": request_counts,
            "auth_failures": dict(self.auth_failure_counts),
            "avg_response_times_ms": avg_response_times,
            "total_requests": sum(
                metrics["count"] for metrics in self.request_metrics.values()
            ),
            "total_auth_failures": sum(self.auth_failure_counts.values()),
        }

    def reset_metrics(self) -> None:
        """Reset all collected metrics."""
        self.request_metrics.clear()
        self.auth_failure_counts.clear()
