"""Tests for API key API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import httpx
import pytest

from tests.conftest import AsyncSessionContext

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.database.models import Device, WireGuardNetwork


@pytest.mark.asyncio
async def test_create_api_key(
    test_network: WireGuardNetwork,
    test_device: Device,
    unlocked_master_password: str,
    client: httpx.AsyncClient,
) -> None:
    """Test creating a new API key."""

    api_key_data = {
        "name": "Test API Key",
        "device_id": test_device.id,
        "allowed_ip_ranges": "192.168.1.0/24,10.0.0.1",
        "enabled": True,
        "expires_at": None,
    }

    response = await client.post("/api/api-keys/", json=api_key_data)

    if response.status_code != 201:
        print(f"DEBUG: Response status: {response.status_code}")
        print(f"DEBUG: Response body: {response.text}")

    assert response.status_code == 201
    data = response.json()
    assert data["api_key"]["name"] == "Test API Key"
    assert data["api_key"]["device_id"] == test_device.id
    assert data["api_key"]["network_id"] == test_network.id
    assert data["api_key"]["allowed_ip_ranges"] == "192.168.1.0/24,10.0.0.1"
    assert data["api_key"]["enabled"] is True
    assert data["api_key"]["expires_at"] is None
    assert "key_value" in data
    assert len(data["key_value"]) > 0
    assert "id" in data["api_key"]
    assert "created_at" in data["api_key"]
    assert "updated_at" in data["api_key"]


@pytest.mark.asyncio
async def test_create_api_key_with_expiry(
    test_network: WireGuardNetwork,
    test_device: Device,
    unlocked_master_password: str,
    mock_session: AsyncSession,
    client: httpx.AsyncClient,
    cleanup_dependencies,
) -> None:
    """Test creating an API key with expiry date."""

    future_time = "2026-12-31T23:59:59Z"
    api_key_data = {
        "name": "Test API Key with Expiry",
        "device_id": test_device.id,
        "allowed_ip_ranges": "192.168.1.0/24",
        "enabled": True,
        "expires_at": future_time,
    }

    async with AsyncSessionContext(mock_session):
        response = await client.post("/api/api-keys/", json=api_key_data)

        assert response.status_code == 201
        data = response.json()
        assert data["api_key"]["expires_at"] is not None


@pytest.mark.asyncio
async def test_create_api_key_invalid_device(
    mock_session: AsyncSession, client: httpx.AsyncClient, cleanup_dependencies
) -> None:
    """Test creating an API key with invalid device ID."""

    api_key_data = {
        "name": "Test API Key",
        "device_id": "invalid-device-id",
        "allowed_ip_ranges": "192.168.1.0/24",
        "enabled": True,
    }

    async with AsyncSessionContext(mock_session):
        response = await client.post("/api/api-keys/", json=api_key_data)

        assert response.status_code == 404
        assert "Device with ID" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_api_key_invalid_ip_ranges(
    test_device: Device,
    mock_session: AsyncSession,
    client: httpx.AsyncClient,
    cleanup_dependencies,
) -> None:
    """Test creating an API key with invalid IP ranges."""

    api_key_data = {
        "name": "Test API Key",
        "device_id": test_device.id,
        "allowed_ip_ranges": "invalid-ip-range",
        "enabled": True,
    }

    async with AsyncSessionContext(mock_session):
        response = await client.post("/api/api-keys/", json=api_key_data)

        assert response.status_code == 422
        response_json = response.json()
        assert response_json["error"] == "validation_error"
        assert "Invalid IP range" in response_json["details"][0]["ctx"]["error"]


@pytest.mark.asyncio
async def test_list_api_keys(
    test_network: WireGuardNetwork,
    test_device: Device,
    unlocked_master_password: str,
    mock_session: AsyncSession,
    client: httpx.AsyncClient,
    cleanup_dependencies,
) -> None:
    """Test listing API keys."""

    api_key_data = {
        "name": "Test API Key",
        "device_id": test_device.id,
        "allowed_ip_ranges": "192.168.1.0/24",
        "enabled": True,
    }

    async with AsyncSessionContext(mock_session):
        # Create an API key first
        create_response = await client.post("/api/api-keys/", json=api_key_data)
        assert create_response.status_code == 201

        # List API keys
        response = await client.get("/api/api-keys/")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1


@pytest.mark.asyncio
async def test_list_api_keys_by_device(
    test_device: Device,
    unlocked_master_password: str,
    mock_session: AsyncSession,
    client: httpx.AsyncClient,
    cleanup_dependencies,
) -> None:
    """Test listing API keys filtered by device."""

    api_key_data = {
        "name": "Test API Key",
        "device_id": test_device.id,
        "allowed_ip_ranges": "192.168.1.0/24",
        "enabled": True,
    }

    async with AsyncSessionContext(mock_session):
        # Create an API key first
        create_response = await client.post("/api/api-keys/", json=api_key_data)
        assert create_response.status_code == 201

        # List API keys for the device
        response = await client.get(f"/api/api-keys/device/{test_device.id}")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        for api_key in data:
            assert api_key["device_id"] == test_device.id


@pytest.mark.asyncio
async def test_get_api_key(
    test_device: Device,
    unlocked_master_password: str,
    mock_session: AsyncSession,
    client: httpx.AsyncClient,
    cleanup_dependencies,
) -> None:
    """Test getting a specific API key."""

    api_key_data = {
        "name": "Test API Key",
        "device_id": test_device.id,
        "allowed_ip_ranges": "192.168.1.0/24",
        "enabled": True,
    }

    async with AsyncSessionContext(mock_session):
        # Create an API key first
        create_response = await client.post("/api/api-keys/", json=api_key_data)
        assert create_response.status_code == 201
        api_key_id = create_response.json()["api_key"]["id"]

        # Get the API key
        response = await client.get(f"/api/api-keys/{api_key_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == api_key_id
        assert data["name"] == "Test API Key"


@pytest.mark.asyncio
async def test_get_nonexistent_api_key(
    mock_session: AsyncSession, client: httpx.AsyncClient, cleanup_dependencies
) -> None:
    """Test getting a non-existent API key."""

    async with AsyncSessionContext(mock_session):
        response = await client.get("/api/api-keys/nonexistent-id")

        assert response.status_code == 404
        assert "API key with ID" in response.json()["detail"]


@pytest.mark.asyncio
async def test_update_api_key(
    test_device: Device,
    mock_session: AsyncSession,
    client: httpx.AsyncClient,
    cleanup_dependencies,
) -> None:
    """Test updating an API key."""

    api_key_data = {
        "name": "Test API Key",
        "device_id": test_device.id,
        "allowed_ip_ranges": "192.168.1.0/24",
        "enabled": True,
    }

    async with AsyncSessionContext(mock_session):
        # Create an API key first
        create_response = await client.post("/api/api-keys/", json=api_key_data)
        assert create_response.status_code == 201
        api_key_id = create_response.json()["api_key"]["id"]

        # Update the API key
        update_data = {
            "name": "Updated API Key",
            "allowed_ip_ranges": "10.0.0.0/24",
            "enabled": False,
        }
        response = await client.put(f"/api/api-keys/{api_key_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated API Key"
        assert data["allowed_ip_ranges"] == "10.0.0.0/24"
        assert data["enabled"] is False


@pytest.mark.asyncio
async def test_rotate_api_key(
    test_device: Device,
    unlocked_master_password: str,
    mock_session: AsyncSession,
    client: httpx.AsyncClient,
    cleanup_dependencies,
) -> None:
    """Test rotating an API key."""

    api_key_data = {
        "name": "Test API Key",
        "device_id": test_device.id,
        "allowed_ip_ranges": "192.168.1.0/24",
        "enabled": True,
    }

    async with AsyncSessionContext(mock_session):
        # Create an API key first
        create_response = await client.post("/api/api-keys/", json=api_key_data)
        assert create_response.status_code == 201
        api_key_id = create_response.json()["api_key"]["id"]
        original_key_value = create_response.json()["key_value"]

        # Rotate the API key
        response = await client.post(f"/api/api-keys/{api_key_id}/rotate")

        assert response.status_code == 200
        data = response.json()
        assert "old_key" in data
        assert "new_key" in data
        assert data["old_key"]["enabled"] is False
        assert data["new_key"]["api_key"]["enabled"] is True
        assert data["new_key"]["key_value"] != original_key_value


@pytest.mark.asyncio
async def test_revoke_api_key(
    test_device: Device,
    mock_session: AsyncSession,
    client: httpx.AsyncClient,
    cleanup_dependencies,
) -> None:
    """Test revoking an API key."""

    api_key_data = {
        "name": "Test API Key",
        "device_id": test_device.id,
        "allowed_ip_ranges": "192.168.1.0/24",
        "enabled": True,
    }

    async with AsyncSessionContext(mock_session):
        # Create an API key first
        create_response = await client.post("/api/api-keys/", json=api_key_data)
        assert create_response.status_code == 201
        api_key_id = create_response.json()["api_key"]["id"]

        # Revoke the API key
        response = await client.post(f"/api/api-keys/{api_key_id}/revoke")

        assert response.status_code == 200
        data = response.json()
        assert "revoked successfully" in data["message"]

        # Verify the key is now disabled
        get_response = await client.get(f"/api/api-keys/{api_key_id}")
        assert get_response.status_code == 200
        assert get_response.json()["enabled"] is False


@pytest.mark.asyncio
async def test_delete_api_key(
    test_device: Device,
    mock_session: AsyncSession,
    client: httpx.AsyncClient,
    cleanup_dependencies,
) -> None:
    """Test deleting an API key."""

    api_key_data = {
        "name": "Test API Key",
        "device_id": test_device.id,
        "allowed_ip_ranges": "192.168.1.0/24",
        "enabled": True,
    }

    async with AsyncSessionContext(mock_session):
        # Create an API key first
        create_response = await client.post("/api/api-keys/", json=api_key_data)
        assert create_response.status_code == 201
        api_key_id = create_response.json()["api_key"]["id"]

        # Delete the API key
        response = await client.delete(f"/api/api-keys/{api_key_id}")

        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data["message"]

        # Verify the key no longer exists
        get_response = await client.get(f"/api/api-keys/{api_key_id}")
        assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_create_api_key_past_expiry(
    test_device: Device,
    mock_session: AsyncSession,
    client: httpx.AsyncClient,
    cleanup_dependencies,
) -> None:
    """Test creating an API key with past expiry date."""

    past_time = "2020-01-01T00:00:00Z"
    api_key_data = {
        "name": "Test API Key",
        "device_id": test_device.id,
        "allowed_ip_ranges": "192.168.1.0/24",
        "enabled": True,
        "expires_at": past_time,
    }

    async with AsyncSessionContext(mock_session):
        response = await client.post("/api/api-keys/", json=api_key_data)

        assert response.status_code == 400
        assert "Expiry time must be in the future" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_api_key_invalid_expiry_format(
    test_device: Device,
    mock_session: AsyncSession,
    client: httpx.AsyncClient,
    cleanup_dependencies,
) -> None:
    """Test creating an API key with invalid expiry format."""

    api_key_data = {
        "name": "Test API Key",
        "device_id": test_device.id,
        "allowed_ip_ranges": "192.168.1.0/24",
        "enabled": True,
        "expires_at": "invalid-date-format",
    }

    async with AsyncSessionContext(mock_session):
        response = await client.post("/api/api-keys/", json=api_key_data)

        assert response.status_code == 400
        assert "Invalid expiry timestamp format" in response.json()["detail"]
