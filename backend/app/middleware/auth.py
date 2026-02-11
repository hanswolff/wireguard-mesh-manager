"""Authentication middleware for validating master sessions."""

from __future__ import annotations

import hashlib
from typing import Any

from dataclasses import dataclass

from fastapi import HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


@dataclass(frozen=True)
class MasterSessionInfo:
    """Master session information attached to requests."""

    session_id: str
    actor: str
    ip_address: str | None
    user_agent: str | None


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware to authenticate admin access via master sessions."""

    # Paths that don't require authentication
    PUBLIC_PATHS = {
        "/health",
        "/ready",
        "/metrics",
        "/csrf/token",
        "/csrf/settings",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/",  # Root endpoint
        "/master-password/unlock",
        "/master-password/is-unlocked",  # Public endpoint to check if cache is unlocked
        "/api/master-password/unlock",  # Frontend calls this
        "/api/master-password/is-unlocked",  # Public endpoint to check if cache is unlocked
        "/api/health",
        "/api/ready",
        "/api/metrics",
        "/api/csrf/token",
        "/api/csrf/settings",
        "/api",  # API root endpoint
        # Support for device config paths with parameter placeholders
        # Note: These will be matched with path prefix logic
    }

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and add user to request state if authenticated."""
        if getattr(request.app.state, "bypass_auth", False):
            if not (
                request.url.path.startswith("/api/devices/")
                and "/config" in request.url.path
                and not request.url.path.startswith("/api/devices/admin")
            ):
                request.state.master_session = MasterSessionInfo(
                    session_id="test-session",
                    actor="master-session:test",
                    ip_address="127.0.0.1",
                    user_agent="pytest",
                )
            response = await call_next(request)
            return response

        # Skip authentication for public paths
        if request.url.path in self.PUBLIC_PATHS:
            response = await call_next(request)
            return response

        # Skip authentication for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            response = await call_next(request)
            return response

        # Skip authentication for device self-service config endpoints
        # These endpoints handle their own API key authentication
        if (
            request.url.path.startswith("/api/devices/")
            and "/config" in request.url.path
            and not request.url.path.startswith("/api/devices/admin")
        ):
            response = await call_next(request)
            return response

        # Allow GET requests to /api/settings without authentication
        # (read-only access to operational settings for UI customization)
        if request.url.path == "/api/settings" and request.method == "GET":
            response = await call_next(request)
            return response

        # Extract master session token from Authorization header
        authorization = request.headers.get("authorization")
        if not authorization or not authorization.startswith("Master "):
            await self._log_auth_failure(
                request=request,
                reason="missing_or_invalid_auth_header",
            )
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing or invalid Authorization header"},
                headers={"WWW-Authenticate": "Master"},
            )

        session_token = authorization[7:]  # Remove "Master " prefix

        # Validate session token with client binding
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("User-Agent")
        session_info = await self._validate_session_token(
            request, session_token, client_ip, user_agent
        )
        if not session_info:
            await self._log_auth_failure(
                request=request,
                reason="invalid_or_expired_master_session",
                session_token=session_token,
            )
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or expired master session token"},
                headers={"WWW-Authenticate": "Master"},
            )

        request.state.master_session = session_info
        response = await call_next(request)
        return response

    async def _log_auth_failure(
        self,
        request: Request,
        reason: str,
        session_token: str | None = None,
    ) -> None:
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("User-Agent")
        session_fingerprint = None
        if session_token:
            session_fingerprint = hashlib.sha256(session_token.encode()).hexdigest()[:16]

        db, db_context = await self._get_db_session(request)
        if not db:
            return

        try:
            from app.services.audit import AuditService

            audit_service = AuditService(db)
            await audit_service.log_event(
                network_id=None,
                actor=f"ip:{client_ip}" if client_ip else "unknown",
                action="ACCESS_DENIED",
                resource_type="master_session",
                resource_id=session_fingerprint,
                details={
                    "reason": reason,
                    "source_ip": client_ip,
                    "user_agent": user_agent,
                    "path": request.url.path,
                    "method": request.method,
                    "master_header_present": bool(
                        request.headers.get("authorization")
                    ),
                    "session_fingerprint": session_fingerprint,
                },
            )
        except Exception:
            # Avoid auth failures cascading due to audit logging issues.
            return
        finally:
            if db_context is not None:
                try:
                    if hasattr(db_context, "aclose"):
                        await db_context.aclose()
                except Exception:
                    return

    async def _validate_session_token(
        self,
        request: Request,
        session_token: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ):
        """Validate session token and return session info if valid."""
        try:
            from app.services.master_session import (
                format_master_actor,
                master_session_manager,
            )

            session = master_session_manager.get_session(
                session_token,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            if not session:
                return None
            return MasterSessionInfo(
                session_id=session.session_id,
                actor=format_master_actor(session.session_id),
                ip_address=ip_address,
                user_agent=user_agent,
            )
        except Exception:
            # Log the error for debugging but don't expose details to client
            import logging

            logger = logging.getLogger(__name__)
            logger.exception("Master session token validation error")
            return None

    def _get_client_ip(self, request: Request) -> str | None:
        """Get the real client IP, validating forwarded headers only from trusted proxies."""
        import ipaddress

        from app.config import settings

        # Parse trusted proxy CIDR ranges
        trusted_proxies: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
        if settings.trusted_proxies:
            for proxy in settings.trusted_proxies.split(","):
                proxy = proxy.strip()
                if proxy:
                    try:
                        trusted_proxies.append(
                            ipaddress.ip_network(proxy, strict=False)
                        )
                    except ValueError:
                        # Skip invalid proxy configurations
                        continue

        # Get the direct connection IP
        direct_ip = None
        if hasattr(request, "client") and request.client:
            direct_ip = request.client.host

        # Check if the direct connection is from a trusted proxy
        is_trusted_proxy = False
        if direct_ip and trusted_proxies:
            try:
                client_ip = ipaddress.ip_address(direct_ip)
                is_trusted_proxy = any(
                    client_ip in proxy_network for proxy_network in trusted_proxies
                )
            except ValueError:
                # Invalid IP format, don't trust any forwarded headers
                is_trusted_proxy = False

        # Only trust forwarded headers if they come from a trusted proxy
        if is_trusted_proxy:
            # Check X-Forwarded-For header
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                # X-Forwarded-For can contain multiple IPs, the original client is first
                original_ip = forwarded_for.split(",")[0].strip()
                if original_ip:
                    return original_ip

            # Check X-Real-IP header
            real_ip = request.headers.get("X-Real-IP")
            if real_ip:
                cleaned_ip = real_ip.strip()
                if cleaned_ip:
                    return cleaned_ip

        # Fall back to direct connection IP
        return direct_ip

    async def _get_db_session(self, request: Request) -> tuple[Any | None, Any | None]:
        state = getattr(request, "state", None)
        if state is not None and hasattr(state, "db"):
            return getattr(state, "db"), None

        try:
            from app.database.connection import get_db

            dependency = request.app.dependency_overrides.get(get_db, get_db)
            db_context = dependency()
            if hasattr(db_context, "__anext__"):
                try:
                    db = await db_context.__anext__()
                except StopAsyncIteration:
                    return None, None
                return db, db_context
            return db_context, None
        except Exception:
            return None, None


def require_master_session(request: Request) -> None:
    """Dependency that requires an authenticated master session."""
    if not hasattr(request.state, "master_session") or not request.state.master_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Master session authentication required",
            headers={"WWW-Authenticate": "Master"},
        )


def get_master_session(request: Request) -> MasterSessionInfo | None:
    """Dependency that gets the current master session if authenticated."""
    return getattr(request.state, "master_session", None)
