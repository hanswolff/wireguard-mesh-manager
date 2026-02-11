"""Tests for API key service."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from app.schemas.devices import APIKeyCreate, APIKeyUpdate
from app.services.api_key import APIKeyService
from app.utils.api_key import (
    APIKeyNotFoundError,
    DeviceNotFoundError,
    compute_api_key_fingerprint,
    generate_api_key,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.database.models import Device, WireGuardNetwork


def _generate_key_material() -> tuple[str, str, str]:
    """Generate API key value, hash, and fingerprint for tests."""
    key_value, key_hash = generate_api_key()
    key_fingerprint = compute_api_key_fingerprint(key_value)
    return key_value, key_hash, key_fingerprint


@pytest.mark.asyncio
async def test_api_key_service_create_key(
    test_network: WireGuardNetwork, test_device: Device, mock_session: AsyncSession
) -> None:
    """Test creating an API key through the service."""
    service = APIKeyService(mock_session)

    key_value, key_hash, key_fingerprint = _generate_key_material()
    api_key_data = APIKeyCreate(
        name="Test Key",
        device_id=test_device.id,
        allowed_ip_ranges="192.168.1.0/24",
        enabled=True,
    )

    api_key = await service.create_api_key(
        api_key_data, key_hash, key_fingerprint
    )

    assert api_key.name == "Test Key"
    assert api_key.device_id == test_device.id
    assert api_key.network_id == test_network.id
    assert api_key.key_hash == key_hash
    assert api_key.allowed_ip_ranges == "192.168.1.0/24"
    assert api_key.enabled is True
    assert api_key.expires_at is None


@pytest.mark.asyncio
async def test_api_key_service_create_key_with_expiry(
    test_device: Device, mock_session: AsyncSession
) -> None:
    """Test creating an API key with expiry through the service."""
    service = APIKeyService(mock_session)

    key_value, key_hash, key_fingerprint = _generate_key_material()
    api_key_data = APIKeyCreate(
        name="Test Key with Expiry",
        device_id=test_device.id,
        allowed_ip_ranges="192.168.1.0/24",
        enabled=True,
        expires_at="2026-12-31T23:59:59Z",
    )

    api_key = await service.create_api_key(
        api_key_data, key_hash, key_fingerprint
    )

    assert api_key.expires_at is not None


@pytest.mark.asyncio
async def test_api_key_service_create_key_invalid_device(
    mock_session: AsyncSession,
) -> None:
    """Test creating an API key with invalid device ID."""
    service = APIKeyService(mock_session)

    key_value, key_hash, key_fingerprint = _generate_key_material()
    api_key_data = APIKeyCreate(
        name="Test Key",
        device_id="invalid-device-id",
        allowed_ip_ranges="192.168.1.0/24",
        enabled=True,
    )

    with pytest.raises(DeviceNotFoundError):
        await service.create_api_key(api_key_data, key_hash, key_fingerprint)


@pytest.mark.asyncio
async def test_api_key_service_list_keys(
    test_device: Device, mock_session: AsyncSession
) -> None:
    """Test listing API keys through the service."""
    service = APIKeyService(mock_session)

    # Create a key first
    key_value, key_hash, key_fingerprint = _generate_key_material()
    api_key_data = APIKeyCreate(
        name="Test Key",
        device_id=test_device.id,
        allowed_ip_ranges="192.168.1.0/24",
        enabled=True,
    )
    await service.create_api_key(api_key_data, key_hash, key_fingerprint)

    # List all keys
    keys = await service.list_api_keys()
    assert len(keys) >= 1

    # List keys for specific device
    device_keys = await service.list_api_keys(device_id=test_device.id)
    assert len(device_keys) >= 1
    for key in device_keys:
        assert key.device_id == test_device.id


@pytest.mark.asyncio
async def test_api_key_service_get_key(
    test_device: Device, mock_session: AsyncSession
) -> None:
    """Test getting a specific API key through the service."""
    service = APIKeyService(mock_session)

    # Create a key first
    key_value, key_hash, key_fingerprint = _generate_key_material()
    api_key_data = APIKeyCreate(
        name="Test Key",
        device_id=test_device.id,
        allowed_ip_ranges="192.168.1.0/24",
        enabled=True,
    )
    created_key = await service.create_api_key(
        api_key_data, key_hash, key_fingerprint
    )

    # Get the key
    retrieved_key = await service.get_api_key(created_key.id)
    assert retrieved_key.id == created_key.id
    assert retrieved_key.name == "Test Key"


@pytest.mark.asyncio
async def test_api_key_service_get_nonexistent_key(mock_session: AsyncSession) -> None:
    """Test getting a non-existent API key."""
    service = APIKeyService(mock_session)

    with pytest.raises(APIKeyNotFoundError):
        await service.get_api_key("nonexistent-key-id")


@pytest.mark.asyncio
async def test_api_key_service_get_keys_by_device(
    test_device: Device, mock_session: AsyncSession
) -> None:
    """Test getting API keys for a specific device."""
    service = APIKeyService(mock_session)

    # Create a key first
    key_value, key_hash, key_fingerprint = _generate_key_material()
    api_key_data = APIKeyCreate(
        name="Test Key",
        device_id=test_device.id,
        allowed_ip_ranges="192.168.1.0/24",
        enabled=True,
    )
    await service.create_api_key(api_key_data, key_hash, key_fingerprint)

    # Get keys for the device
    device_keys = await service.get_api_keys_by_device(test_device.id)
    assert len(device_keys) >= 1
    for key in device_keys:
        assert key.device_id == test_device.id


@pytest.mark.asyncio
async def test_api_key_service_get_keys_by_invalid_device(
    mock_session: AsyncSession,
) -> None:
    """Test getting API keys for an invalid device."""
    service = APIKeyService(mock_session)

    with pytest.raises(DeviceNotFoundError):
        await service.get_api_keys_by_device("invalid-device-id")


@pytest.mark.asyncio
async def test_api_key_service_update_key(
    test_device: Device, mock_session: AsyncSession
) -> None:
    """Test updating an API key through the service."""
    service = APIKeyService(mock_session)

    # Create a key first
    key_value, key_hash, key_fingerprint = _generate_key_material()
    api_key_data = APIKeyCreate(
        name="Test Key",
        device_id=test_device.id,
        allowed_ip_ranges="192.168.1.0/24",
        enabled=True,
    )
    created_key = await service.create_api_key(
        api_key_data, key_hash, key_fingerprint
    )

    # Update the key
    update_data = APIKeyUpdate(
        name="Updated Key",
        allowed_ip_ranges="10.0.0.0/24",
        enabled=False,
        expires_at="2026-12-31T23:59:59Z",
    )
    updated_key = await service.update_api_key(created_key.id, update_data)

    assert updated_key.name == "Updated Key"
    assert updated_key.allowed_ip_ranges == "10.0.0.0/24"
    assert updated_key.enabled is False
    assert updated_key.expires_at is not None


@pytest.mark.asyncio
async def test_api_key_service_update_key_remove_expiry(
    test_device: Device, mock_session: AsyncSession
) -> None:
    """Test updating an API key to remove expiry."""
    service = APIKeyService(mock_session)

    # Create a key with expiry first
    key_value, key_hash, key_fingerprint = _generate_key_material()
    api_key_data = APIKeyCreate(
        name="Test Key",
        device_id=test_device.id,
        allowed_ip_ranges="192.168.1.0/24",
        enabled=True,
        expires_at="2026-12-31T23:59:59Z",
    )
    created_key = await service.create_api_key(
        api_key_data, key_hash, key_fingerprint
    )

    # Remove expiry
    update_data = APIKeyUpdate(expires_at="")
    updated_key = await service.update_api_key(created_key.id, update_data)

    assert updated_key.expires_at is None


@pytest.mark.asyncio
async def test_api_key_service_update_nonexistent_key(
    mock_session: AsyncSession,
) -> None:
    """Test updating a non-existent API key."""
    service = APIKeyService(mock_session)

    update_data = APIKeyUpdate(name="Updated Key")

    with pytest.raises(APIKeyNotFoundError):
        await service.update_api_key("nonexistent-key-id", update_data)


@pytest.mark.asyncio
async def test_api_key_service_rotate_key(
    test_device: Device, mock_session: AsyncSession
) -> None:
    """Test rotating an API key through the service."""
    service = APIKeyService(mock_session)

    # Create a key first
    key_value, key_hash, key_fingerprint = _generate_key_material()
    api_key_data = APIKeyCreate(
        name="Test Key",
        device_id=test_device.id,
        allowed_ip_ranges="192.168.1.0/24",
        enabled=True,
    )
    created_key = await service.create_api_key(
        api_key_data, key_hash, key_fingerprint
    )

    # Rotate the key
    new_key_value, new_key_hash, new_key_fingerprint = _generate_key_material()
    new_key = await service.rotate_api_key(
        created_key.id, new_key_hash, new_key_fingerprint
    )

    assert new_key.name == "Test Key"
    assert new_key.device_id == test_device.id
    assert new_key.key_hash == new_key_hash
    assert new_key.enabled is True

    # Verify old key is disabled
    old_key = await service.get_api_key(created_key.id)
    assert old_key.enabled is False
    assert "rotated" in old_key.name


@pytest.mark.asyncio
async def test_api_key_service_rotate_nonexistent_key(
    mock_session: AsyncSession,
) -> None:
    """Test rotating a non-existent API key."""
    service = APIKeyService(mock_session)

    key_value, key_hash, key_fingerprint = _generate_key_material()

    with pytest.raises(APIKeyNotFoundError):
        await service.rotate_api_key(
            "nonexistent-key-id", key_hash, key_fingerprint
        )


@pytest.mark.asyncio
async def test_api_key_service_revoke_key(
    test_device: Device, mock_session: AsyncSession
) -> None:
    """Test revoking an API key through the service."""
    service = APIKeyService(mock_session)

    # Create a key first
    key_value, key_hash, key_fingerprint = _generate_key_material()
    api_key_data = APIKeyCreate(
        name="Test Key",
        device_id=test_device.id,
        allowed_ip_ranges="192.168.1.0/24",
        enabled=True,
    )
    created_key = await service.create_api_key(
        api_key_data, key_hash, key_fingerprint
    )

    # Revoke the key
    revoked_key = await service.revoke_api_key(created_key.id)

    assert revoked_key.enabled is False
    assert "revoked" in revoked_key.name


@pytest.mark.asyncio
async def test_api_key_service_revoke_nonexistent_key(
    mock_session: AsyncSession,
) -> None:
    """Test revoking a non-existent API key."""
    service = APIKeyService(mock_session)

    with pytest.raises(APIKeyNotFoundError):
        await service.revoke_api_key("nonexistent-key-id")


@pytest.mark.asyncio
async def test_api_key_service_delete_key(
    test_device: Device, mock_session: AsyncSession
) -> None:
    """Test deleting an API key through the service."""
    service = APIKeyService(mock_session)

    # Create a key first
    key_value, key_hash, key_fingerprint = _generate_key_material()
    api_key_data = APIKeyCreate(
        name="Test Key",
        device_id=test_device.id,
        allowed_ip_ranges="192.168.1.0/24",
        enabled=True,
    )
    created_key = await service.create_api_key(
        api_key_data, key_hash, key_fingerprint
    )

    # Delete the key
    await service.delete_api_key(created_key.id)

    # Verify the key no longer exists
    with pytest.raises(APIKeyNotFoundError):
        await service.get_api_key(created_key.id)


@pytest.mark.asyncio
async def test_api_key_service_delete_nonexistent_key(
    mock_session: AsyncSession,
) -> None:
    """Test deleting a non-existent API key."""
    service = APIKeyService(mock_session)

    with pytest.raises(APIKeyNotFoundError):
        await service.delete_api_key("nonexistent-key-id")
