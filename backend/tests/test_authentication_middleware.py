"""Integration tests for authentication middleware."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from fastapi import status
from sqlalchemy import desc, select

if TYPE_CHECKING:
    from httpx import AsyncClient


async def test_public_routes_accessible_without_auth(client: AsyncClient) -> None:
    """Test that public routes are accessible without authentication."""
    public_routes = [
        "/",
        "/health",
        "/ready",
        "/metrics",
        "/csrf/token",
        "/csrf/settings",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/master-password/unlock",
        "/api",
        "/api/health",
        "/api/ready",
        "/api/metrics",
    ]

    for route in public_routes:
        response = await client.get(route)
        # All public routes should return 2xx (not 401)
        assert response.status_code not in {
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        }, f"Route {route} should be public but returned {response.status_code}"


async def test_protected_routes_require_auth(client: AsyncClient) -> None:
    """Test that protected routes return 401 without authentication."""
    protected_routes = [
        "/networks",
        "/locations",
        "/devices",
        "/export/networks",
        "/backup/create",
        "/audit/events",
        "/master-password/status",
        "/api/networks",
        "/api/locations",
        "/api/devices",
        "/api/export",
        "/api/backup/create",
        "/api/audit/events",
        "/api/devices/admin/device-id/config",
    ]

    for route in protected_routes:
        response = await client.get(route)
        # All protected routes should return 401
        assert (
            response.status_code == 401
        ), f"Route {route} should require auth but returned {response.status_code}"


async def test_protected_routes_work_with_valid_token(
    client: AsyncClient, master_session_token: str
) -> None:
    """Test that protected routes work with valid authentication token."""
    headers = {
        "Authorization": f"Master {master_session_token}",
        "User-Agent": "test-agent",
    }

    protected_routes = [
        "/networks",
        "/locations",
        "/devices",
        "/api/networks",
        "/api/locations",
        "/api/devices",
    ]

    for route in protected_routes:
        response = await client.get(route, headers=headers)
        # Should not return 401 (may return 200, 404, or other valid response)
        assert (
            response.status_code != 401
        ), f"Route {route} should work with valid token but returned 401"


async def test_invalid_token_rejected(client: AsyncClient, db_session) -> None:
    """Test that invalid tokens are rejected."""
    from app.database.models import AuditEvent

    headers = {"Authorization": "Master invalid_token_here"}

    protected_route = "/networks"
    response = await client.get(protected_route, headers=headers)

    # Should return 401 for invalid token
    assert response.status_code == 401

    result = await db_session.execute(
        select(AuditEvent)
        .where(
            AuditEvent.action == "ACCESS_DENIED",
            AuditEvent.resource_type == "master_session",
        )
        .order_by(desc(AuditEvent.created_at))
    )
    audit_event = result.scalars().first()
    assert audit_event is not None
    details = json.loads(audit_event.details or "{}")
    assert details.get("reason") == "invalid_or_expired_master_session"


async def test_malformed_auth_header_rejected(client: AsyncClient) -> None:
    """Test that malformed authorization headers are rejected."""
    malformed_headers = [
        {"Authorization": "InvalidFormat token"},
        {"Authorization": "Master"},
        {"Authorization": ""},
        {"X-Custom-Auth": "Bearer token"},
    ]

    protected_route = "/networks"

    for headers in malformed_headers:
        response = await client.get(protected_route, headers=headers)
        # Should return 401 for malformed headers
        assert response.status_code == 401


async def test_options_requests_bypass_auth(client: AsyncClient) -> None:
    """Test that OPTIONS requests bypass authentication."""
    # OPTIONS requests should work for any route without auth
    response = await client.options("/protected/route")
    # Should not return 401 (may return 405 Method Not Allowed or 200/204)
    assert response.status_code != 401
