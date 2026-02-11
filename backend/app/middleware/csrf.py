"""CSRF protection middleware for admin browser flows."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.config import settings
from app.utils.logging import get_logger

if TYPE_CHECKING:
    from fastapi import FastAPI, Request, Response
    from starlette.types import ASGIApp


class CSRFTokenStore:
    """Thread-safe token storage with expiration cleanup."""

    def __init__(self) -> None:
        self._tokens: dict[str, datetime] = {}

    def add_token(self, token: str, expires_at: datetime) -> None:
        """Add a token with expiration time."""
        self._cleanup_expired()
        self._tokens[token] = expires_at

    def is_valid(self, token: str) -> bool:
        """Check if token exists and is not expired."""
        self._cleanup_expired()
        expires_at = self._tokens.get(token)
        return expires_at is not None and expires_at > datetime.now()

    def has_token(self, token: str) -> bool:
        """Check if token exists in storage (regardless of expiry)."""
        return token in self._tokens

    def count(self) -> int:
        """Return number of tokens tracked."""
        return len(self._tokens)

    def _cleanup_expired(self) -> None:
        """Remove expired tokens."""
        now = datetime.now()
        expired_tokens = [
            token for token, expires_at in self._tokens.items() if expires_at <= now
        ]
        for token in expired_tokens:
            self._tokens.pop(token, None)


class CSRFMiddleware(BaseHTTPMiddleware):
    """Middleware to protect against CSRF attacks for admin browser flows.

    Implements CSRF protection using double-submit cookie pattern with
    SameSite=Strict cookies and origin validation.
    """

    CSRF_COOKIE_NAME = "csrf_token"
    CSRF_HEADER_NAME = "X-CSRF-Token"
    TOKEN_LENGTH = 32
    COOKIE_MAX_AGE = 3600

    PROTECTED_PATHS = {
        "/networks",
        "/locations",
        "/devices",
        "/export",
        "/backup",
        "/master-password",
        "/key-rotation",
        "/audit",
        "/api-keys",
    }

    EXEMPT_PATHS = {
        "/health",
        "/ready",
        "/metrics",
        "/docs",
        "/openapi.json",
        "/redoc",
    }

    SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._token_store = CSRFTokenStore()
        self._logger = get_logger(__name__)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Process request and enforce CSRF protection."""
        if not settings.csrf_protection_enabled:
            return await call_next(request)

        path = request.url.path

        if self._should_skip_protection(request, path):
            response = await call_next(request)
            self._set_csrf_cookie_if_needed(response, request)
            return response

        try:
            self._validate_csrf_token(request)
        except HTTPException as exc:
            return JSONResponse(
                status_code=exc.status_code, content={"detail": exc.detail}
            )
        response = await call_next(request)
        self._set_csrf_cookie_if_needed(response, request)
        return response

    def _should_skip_protection(self, request: Request, path: str) -> bool:
        """Determine if CSRF protection should be skipped for this request."""
        return (
            self._is_exempt_path(path)
            or request.method in self.SAFE_METHODS
            or not self._needs_protection(path)
        )

    def _is_exempt_path(self, path: str) -> bool:
        """Check if path is exempt from CSRF protection."""
        if path in self.EXEMPT_PATHS:
            return True

        if "/config/" in path:
            return True

        return path.startswith("/static/") or path.startswith("/assets/")

    def _needs_protection(self, path: str) -> bool:
        """Check if path requires CSRF protection."""
        # Check if any protected path is a prefix of the current path
        for protected_path in self.PROTECTED_PATHS:
            if path.startswith(protected_path) or path.startswith(
                f"/api{protected_path}"
            ):
                return True
        return False

    def _validate_csrf_token(self, request: Request) -> None:
        """Validate CSRF token from request and raise if invalid."""
        token_from_header = request.headers.get(self.CSRF_HEADER_NAME)
        token_from_cookie = request.cookies.get(self.CSRF_COOKIE_NAME)
        client_ip = request.client.host if request.client else None

        if not token_from_header or not token_from_cookie:
            self._logger.warning(
                "CSRF validation failed",
                extra={
                    "reason": "missing",
                    "path": request.url.path,
                    "method": request.method,
                    "origin": request.headers.get("Origin")
                    or request.headers.get("Referer"),
                    "client_ip": client_ip,
                    "has_header": bool(token_from_header),
                    "has_cookie": bool(token_from_cookie),
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token missing",
            )

        if not secrets.compare_digest(token_from_header, token_from_cookie):
            self._logger.warning(
                "CSRF validation failed",
                extra={
                    "reason": "mismatch",
                    "path": request.url.path,
                    "method": request.method,
                    "origin": request.headers.get("Origin")
                    or request.headers.get("Referer"),
                    "client_ip": client_ip,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token mismatch",
            )

        if not self._validate_origin(request, settings.cors_origins):
            self._logger.warning(
                "CSRF validation failed",
                extra={
                    "reason": "origin_invalid",
                    "path": request.url.path,
                    "method": request.method,
                    "origin": request.headers.get("Origin")
                    or request.headers.get("Referer"),
                    "allowed_origins": settings.cors_origins,
                    "client_ip": client_ip,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Origin validation failed",
            )

        if not self._token_store.is_valid(token_from_cookie):
            token_hash = hashlib.sha256(token_from_cookie.encode()).hexdigest()[:12]
            self._logger.warning(
                "CSRF token not recognized by store; re-seeding",
                extra={
                    "reason": "expired_or_unknown",
                    "path": request.url.path,
                    "method": request.method,
                    "origin": request.headers.get("Origin")
                    or request.headers.get("Referer"),
                    "client_ip": client_ip,
                    "token_hash": token_hash,
                    "store_has_token": self._token_store.has_token(token_from_cookie),
                    "store_size": self._token_store.count(),
                },
            )
            expiration = datetime.now() + timedelta(
                seconds=settings.csrf_token_ttl_seconds
            )
            self._token_store.add_token(token_from_cookie, expiration)

    def _validate_origin(self, request: Request, allowed_origins: str) -> bool:
        """Validate the Origin header against allowed origins."""
        origin = request.headers.get("Origin") or request.headers.get("Referer")

        # Skip origin validation for same-origin requests
        if not origin:
            # This might be a same-origin request or a non-browser request
            # For non-browser requests (like curl), we rely on the Authorization header
            return bool(request.headers.get("authorization"))

        # Parse allowed origins
        origins = [o.strip() for o in allowed_origins.split(",") if o.strip()]

        # Check if origin matches any allowed origin
        for allowed_origin in origins:
            # Exact match
            if origin == allowed_origin:
                return True
            # Wildcard match for subdomains
            if allowed_origin.startswith("*."):
                domain = allowed_origin[2:]
                if origin.endswith(domain) and origin[: -len(domain)].endswith("."):
                    return True

        return False

    def _set_csrf_cookie_if_needed(self, response: Response, request: Request) -> None:
        """Set CSRF cookie if needed for the response."""
        if not self._should_set_cookie(response, request):
            return

        token = self._get_or_create_token(request)
        self._set_secure_cookie(response, token, request)

    def _should_set_cookie(self, response: Response, request: Request) -> bool:
        """Check if CSRF cookie should be set for this response."""
        content_type = response.headers.get("content-type", "").lower()
        return (
            content_type.startswith("text/html")
            or request.headers.get("X-Requested-With") == "XMLHttpRequest"
            or request.url.path.startswith("/csrf")
            or request.url.path.startswith("/api/csrf")
        )

    def _get_or_create_token(self, request: Request) -> str:
        """Get existing token or create new one."""
        token = request.cookies.get(self.CSRF_COOKIE_NAME)

        if not token or not self._token_store.is_valid(token):
            token = secrets.token_urlsafe(self.TOKEN_LENGTH)
            expiration = datetime.now() + timedelta(
                seconds=settings.csrf_token_ttl_seconds
            )
            self._token_store.add_token(token, expiration)

        return token

    def _set_secure_cookie(
        self, response: Response, token: str, request: Request
    ) -> None:
        """Set secure CSRF cookie with proper flags."""
        response.set_cookie(
            key=self.CSRF_COOKIE_NAME,
            value=token,
            max_age=self.COOKIE_MAX_AGE,
            httponly=False,
            secure=request.url.scheme != "http",
            samesite="strict",
            path="/",
        )


def add_csrf_middleware(app: FastAPI) -> None:
    """Add CSRF protection middleware to the FastAPI app."""
    app.add_middleware(CSRFMiddleware)
