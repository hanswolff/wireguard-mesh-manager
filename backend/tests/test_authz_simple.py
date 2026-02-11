"""Simple test to check if unauthenticated requests are blocked."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

pytestmark = pytest.mark.usefixtures("unlocked_master_password")

if TYPE_CHECKING:
    from httpx import AsyncClient


@pytest.mark.asyncio
async def test_unauthenticated_requests_blocked(
    client: AsyncClient,
) -> None:
    """Test that unauthenticated users cannot access protected routes."""
    protected_routes = [
        "/devices/",
        "/networks/",
        "/api-keys/",
    ]

    for route in protected_routes:
        response = await client.get(route)
        # Should return either 401 (authentication required) or 422 (validation error)
        # Both indicate the route is protected
        assert response.status_code in (
            401,
            422,
        ), f"Route {route} returned {response.status_code}"
