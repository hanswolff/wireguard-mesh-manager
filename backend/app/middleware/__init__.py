"""Middleware package for the WireGuard Mesh Manager API."""

from .auth import AuthenticationMiddleware
from .csrf import CSRFMiddleware, add_csrf_middleware
from .database_session import DatabaseSessionMiddleware
from .error_handlers import add_exception_handlers
from .logging_middleware import LoggingMiddleware
from .metrics import MetricsMiddleware
from .rate_limit import RateLimitMiddleware
from .request_hardening import add_request_hardening_middleware
from .response_hardening import add_response_hardening_middleware

__all__ = [
    "add_request_hardening_middleware",
    "add_response_hardening_middleware",
    "add_csrf_middleware",
    "add_exception_handlers",
    "AuthenticationMiddleware",
    "CSRFMiddleware",
    "MetricsMiddleware",
    "LoggingMiddleware",
    "RateLimitMiddleware",
    "DatabaseSessionMiddleware",
]
