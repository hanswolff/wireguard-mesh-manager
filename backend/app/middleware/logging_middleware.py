"""Middleware for adding request context to structured logs."""

from __future__ import annotations

import urllib.parse
import uuid
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastapi import Request, Response

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to add request context to logs and log request/response information."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        """Process request and add context to logs."""
        request_id, correlation_id = self._generate_request_ids(request)
        self._set_request_context(request, request_id, correlation_id)
        self._log_request_start(request, request_id, correlation_id)

        try:
            response = await call_next(request)
            self._log_request_completion(request, response, request_id, correlation_id)
            self._add_response_headers(response, request_id, correlation_id)
            return response

        except Exception as exc:
            self._log_request_error(request, exc, request_id, correlation_id)
            raise

    def _generate_request_ids(self, request: Request) -> tuple[str, str]:
        """Generate request and correlation IDs."""
        request_id = str(uuid.uuid4())
        correlation_id = request.headers.get("X-Correlation-ID") or request_id
        return request_id, correlation_id

    def _set_request_context(
        self, request: Request, request_id: str, correlation_id: str
    ) -> None:
        """Add context to request state for use in other parts of the app."""
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id

    def _redact_url(self, url: str) -> str:
        """Redact sensitive information from URLs."""
        parsed = urllib.parse.urlparse(url)
        # Remove query parameters entirely as they may contain sensitive data
        redacted = urllib.parse.urlunparse(parsed._replace(query=""))
        return redacted

    def _log_request_start(
        self, request: Request, request_id: str, correlation_id: str
    ) -> None:
        """Log the start of a request."""
        # Redact sensitive information from the URL
        redacted_url = self._redact_url(str(request.url))

        logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "correlation_id": correlation_id,
                "method": request.method,
                "url": redacted_url,
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("User-Agent"),
            },
        )

    def _log_request_completion(
        self, request: Request, response: Response, request_id: str, correlation_id: str
    ) -> None:
        """Log the completion of a request."""
        # Redact sensitive information from the URL
        redacted_url = self._redact_url(str(request.url))

        logger.info(
            "Request completed",
            extra={
                "request_id": request_id,
                "correlation_id": correlation_id,
                "method": request.method,
                "url": redacted_url,
                "status_code": response.status_code,
            },
        )

    def _log_request_error(
        self, request: Request, exc: Exception, request_id: str, correlation_id: str
    ) -> None:
        """Log a request error."""
        # Redact sensitive information from the URL
        redacted_url = self._redact_url(str(request.url))

        # Redact potentially sensitive exception messages
        exception_msg = str(exc)
        # Look for patterns that suggest sensitive data
        sensitive_patterns = [
            "private_key",
            "password",
            "secret",
            "token",
            "key",
            "credential",
        ]
        if any(
            pattern.lower() in exception_msg.lower() for pattern in sensitive_patterns
        ):
            exception_msg = "Sensitive information in exception message - redacted"

        logger.error(
            "Request failed with exception",
            extra={
                "request_id": request_id,
                "correlation_id": correlation_id,
                "method": request.method,
                "url": redacted_url,
                "exception_type": type(exc).__name__,
                "exception_message": exception_msg,
            },
            exc_info=True,
        )

    def _add_response_headers(
        self, response: Response, request_id: str, correlation_id: str
    ) -> None:
        """Add response headers for request tracking."""
        response.headers["X-Request-ID"] = request_id
        if correlation_id != request_id:
            response.headers["X-Correlation-ID"] = correlation_id
