from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.database import connection
from app.schemas.device_config import DeviceConfigResponse
from app.services.device_config import DeviceConfigService

if TYPE_CHECKING:
    from httpx import AsyncClient


@pytest.fixture(autouse=True)
async def override_async_session_local(db_session: AsyncSession):
    """Ensure middleware uses the test database session factory."""

    connection.AsyncSessionLocal = async_sessionmaker(
        db_session.bind, class_=AsyncSession, expire_on_commit=False
    )
    yield


@pytest.mark.asyncio
async def test_device_list_requires_master_session(
    client: AsyncClient,
) -> None:
    """Listing devices should require a master session."""

    response = await client.get("/api/devices/")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_device_get_requires_master_session(
    client: AsyncClient, test_device
) -> None:
    """Fetching a single device requires a master session."""

    response = await client.get(f"/api/devices/{test_device.id}")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_available_ips_require_authentication(
    client: AsyncClient, test_network
) -> None:
    """Available IPs endpoint should reject unauthenticated callers."""

    response = await client.get(
        f"/api/devices/network/{test_network.id}/available-ips"
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_device_list_allows_master_session(
    client: AsyncClient, master_session_token: str
) -> None:
    """Master sessions should be able to list devices."""

    response = await client.get(
        "/api/devices/", headers={"Authorization": f"Master {master_session_token}"}
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_admin_config_requires_auth(
    async_client: AsyncClient, test_device
) -> None:
    """Admin configuration endpoints must not bypass authentication."""

    response = await async_client.get(f"/api/devices/admin/{test_device.id}/config")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_config_allows_master_session(
    async_client: AsyncClient,
    test_device,
    master_session_token: str,
    unlocked_master_password: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Authenticated master sessions should be able to retrieve admin configs."""

    monkeypatch.setattr(
        DeviceConfigService,
        "decrypt_device_private_key",
        AsyncMock(return_value="private"),
    )

    async def fake_generate_device_config(
        self,
        *,
        device,
        device_private_key: str,
        format_type: str = "wg",
        platform: str | None = None,
        device_dek: str | None = None,
    ):
        return DeviceConfigResponse(
            device_id=device.id,
            device_name=device.name,
            network_name="Test Network",
            configuration="[Interface]\nPrivateKey = private",
            format=format_type,
            created_at="2024-01-01T00:00:00Z",
        )

    monkeypatch.setattr(
        DeviceConfigService, "generate_device_config", fake_generate_device_config
    )

    response = await async_client.get(
        f"/api/devices/admin/{test_device.id}/config",
        headers={"Authorization": f"Master {master_session_token}"},
    )

    assert response.status_code == 200
    assert response.json()["device_id"] == str(test_device.id)
