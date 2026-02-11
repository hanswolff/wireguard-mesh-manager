"""API routes for CSRF protection."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.config import settings

router = APIRouter(tags=["csrf"])


class CSRFTokenResponse(BaseModel):
    """Response model for CSRF token endpoint."""

    csrf_token: str


class SecurityHeadersResponse(BaseModel):
    """Response model for security headers."""

    content_type_options: str = Field(alias="contentTypeOptions")
    frame_options: str = Field(alias="frameOptions")
    xss_protection: str = Field(alias="xssProtection")
    referrer_policy: str = Field(alias="referrerPolicy")
    content_security_policy: str = Field(alias="contentSecurityPolicy")


class SecuritySettingsResponse(BaseModel):
    """Response model for security settings endpoint."""

    cors_origins: str
    csrf_protection_enabled: bool
    trusted_proxies: str
    security_headers: SecurityHeadersResponse


@router.get("/token", response_model=CSRFTokenResponse)
async def get_csrf_token() -> CSRFTokenResponse:
    """
    Get CSRF token for frontend forms.

    Returns a placeholder response. The actual token is set by the
    middleware as a secure cookie with SameSite=Strict.
    Frontend should read the token from the cookie and include it
    in the X-CSRF-Token header for state-changing requests.
    """
    return CSRFTokenResponse(
        csrf_token="Token set in cookie - read from X-CSRF-Token header"
    )


@router.get("/settings", response_model=SecuritySettingsResponse)
async def get_security_settings() -> SecuritySettingsResponse:
    """
    Get current security-related operational settings.

    Returns configuration values that the frontend needs for security features.
    """
    return SecuritySettingsResponse(
        cors_origins=settings.cors_origins,
        csrf_protection_enabled=settings.csrf_protection_enabled,
        trusted_proxies=settings.trusted_proxies or "None configured (deny-by-default)",
        security_headers=_get_security_headers(),
    )


def _get_security_headers() -> SecurityHeadersResponse:
    """Get configured security headers."""
    return SecurityHeadersResponse(
        contentTypeOptions="nosniff",
        frameOptions="DENY",
        xssProtection="1; mode=block",
        referrerPolicy="strict-origin-when-cross-origin",
        contentSecurityPolicy=(
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'"
        ),
    )
