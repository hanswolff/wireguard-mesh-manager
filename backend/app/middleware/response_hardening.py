"""Response hardening middleware for security."""

from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

if TYPE_CHECKING:
    from fastapi import FastAPI, Request, Response
    from starlette.types import ASGIApp


class ResponseHardeningMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers and prevent caching of sensitive responses."""

    SECURITY_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Server": "",
    }

    CSP_HEADER = (
        "default-src 'none'; "
        "script-src 'none'; "
        "style-src 'none'; "
        "img-src 'none'; "
        "font-src 'none'; "
        "connect-src 'none'; "
        "frame-ancestors 'none'; "
        "base-uri 'self';"
    )

    SENSITIVE_CACHE_CONTROL = "no-cache, no-store, must-revalidate, private"
    API_CACHE_CONTROL = "no-cache, must-revalidate, private"
    VARY_HEADER = "Accept-Encoding, Cookie, Authorization"

    SENSITIVE_PATHS = [
        "/config",
        "/api-key",
        "/api_key",
        "/auth",
        "/login",
        "/logout",
        "/session",
        "/master-password",
        "/unlock",
        "/encrypt",
        "/decrypt",
        "/backup",
        "/export",
        "/download",
    ]

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Add security headers to all responses."""
        response = await call_next(request)

        self._add_security_headers(response)
        self._add_content_security_policy(response, request)
        self._add_cache_control_headers(response, request)
        self._enforce_content_type(response, request)

        return response

    def _add_security_headers(self, response: Response) -> None:
        """Add basic security headers to all responses."""
        for header, value in self.SECURITY_HEADERS.items():
            response.headers[header] = value

    def _add_content_security_policy(
        self, response: Response, request: Request
    ) -> None:
        """Add CSP header for non-API endpoints."""
        if self._needs_content_security_policy(request):
            response.headers["Content-Security-Policy"] = self.CSP_HEADER

    def _add_cache_control_headers(self, response: Response, request: Request) -> None:
        """Add appropriate cache control headers based on endpoint sensitivity."""
        if self._is_sensitive_endpoint(request):
            response.headers["Cache-Control"] = self.SENSITIVE_CACHE_CONTROL
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            response.headers["Vary"] = self.VARY_HEADER
        elif self._is_api_endpoint(request):
            response.headers["Cache-Control"] = self.API_CACHE_CONTROL
            response.headers["Vary"] = self.VARY_HEADER

    def _needs_content_security_policy(self, request: Request) -> bool:
        """Determine if CSP header should be added.

        CSP is primarily for web pages, not API endpoints.
        We skip it for API endpoints to avoid unnecessary headers.
        """
        path = request.url.path
        # Skip CSP for API endpoints and config downloads
        return not (path.startswith("/api/") or "/config" in path)

    def _is_sensitive_endpoint(self, request: Request) -> bool:
        """Identify endpoints that contain sensitive information that should never be cached."""
        path = request.url.path.lower()

        # Check if path contains any sensitive segments
        if any(sensitive in path for sensitive in self.SENSITIVE_PATHS):
            return True

        # Admin operations that might expose sensitive data
        return request.method in {"POST", "PUT", "DELETE", "PATCH"}

    def _is_api_endpoint(self, request: Request) -> bool:
        """Identify API endpoints vs web UI endpoints."""
        path = request.url.path
        return path.startswith("/api/")

    def _enforce_content_type(self, response: Response, request: Request) -> None:
        """Enforce proper content type handling and prevent content type sniffing."""
        path = request.url.path
        content_type = response.headers.get("content-type")
        is_json_response = (
            response.media_type == "application/json"
            or (content_type or "").startswith("application/json")
        )

        # For API endpoints, ensure proper content type
        if (
            self._is_api_endpoint(request)
            and is_json_response
            and "content-type" not in {k.lower() for k in response.headers}
        ):
            response.headers["Content-Type"] = "application/json; charset=utf-8"

        # For config downloads, enforce plain text with download disposition,
        # but don't override JSON config responses.
        if "/config" in path and not is_json_response:
            response.headers["Content-Type"] = "text/plain; charset=utf-8"
            if "Content-Disposition" not in response.headers:
                response.headers["Content-Disposition"] = (
                    'attachment; filename="wg0.conf"'
                )


def add_response_hardening_middleware(app: FastAPI) -> None:
    """Add response hardening middleware to the FastAPI app."""
    app.add_middleware(ResponseHardeningMiddleware)
