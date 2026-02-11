"""Test edge cases and error handling for device service."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from app.exceptions import ResourceNotFoundError
from pydantic import ValidationError

from app.schemas.devices import DeviceCreate, DeviceUpdate
from app.services.devices import DeviceService
from tests.conftest import AsyncSessionContext

pytestmark = pytest.mark.usefixtures("unlocked_master_password")

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.database.models import Location, WireGuardNetwork


@pytest.mark.asyncio
async def test_create_device_empty_name(
    test_network: WireGuardNetwork, test_location: Location, mock_session: AsyncSession
) -> None:
    """Test creating device with empty name (should fail validation)."""
    DeviceService(mock_session)

    with pytest.raises(ValidationError) as exc_info:
        DeviceCreate(
            network_id=test_network.id,
            location_id=test_location.id,
            name="",  # Empty name
            
            private_key="xjJIFL7i1+OOOeEyTER40wp58zTkAyY/NzW8sorMNK8=",
        public_key="dvUxLu9pLzLgE4cmB+a8GYGoNr6Z8Utoj3j7KSA7EUE=",
        )

    # Check that the validation error is about the name being too short
    assert "name" in str(exc_info.value)
    assert "String should have at least 1 character" in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_device_oversized_name(
    test_network: WireGuardNetwork, test_location: Location, mock_session: AsyncSession
) -> None:
    """Test creating device with name exceeding max length."""
    DeviceService(mock_session)

    with pytest.raises(ValidationError) as exc_info:
        DeviceCreate(
            network_id=test_network.id,
            location_id=test_location.id,
            name="a" * 101,  # Exceeds 100 char limit
            
            private_key="xjJIFL7i1+OOOeEyTER40wp58zTkAyY/NzW8sorMNK8=",
        public_key="dvUxLu9pLzLgE4cmB+a8GYGoNr6Z8Utoj3j7KSA7EUE=",
        )

    # Check that the validation error is about the name being too long
    assert "name" in str(exc_info.value)
    assert "String should have at most 100 characters" in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_device_oversized_description(
    test_network: WireGuardNetwork, test_location: Location, mock_session: AsyncSession
) -> None:
    """Test creating device with description exceeding max length."""
    DeviceService(mock_session)

    with pytest.raises(ValidationError) as exc_info:
        DeviceCreate(
            network_id=test_network.id,
            location_id=test_location.id,
            name="test-device",
            description="a" * 1001,  # Exceeds 1000 char limit
            
            private_key="xjJIFL7i1+OOOeEyTER40wp58zTkAyY/NzW8sorMNK8=",
        public_key="dvUxLu9pLzLgE4cmB+a8GYGoNr6Z8Utoj3j7KSA7EUE=",
        )

    # Check that the validation error is about the description being too long
    assert "description" in str(exc_info.value)
    assert "String should have at most 1000 characters" in str(exc_info.value)


@pytest.mark.asyncio
async def test_update_device_no_changes(
    test_network: WireGuardNetwork, test_location: Location, mock_session: AsyncSession
) -> None:
    """Test updating device with no actual changes."""
    service = DeviceService(mock_session)

    # Create device first
    device_data = DeviceCreate(
        network_id=test_network.id,
        location_id=test_location.id,
        name="test-device",
        internal_endpoint_host="192.168.1.10",
        internal_endpoint_port=51820,
        private_key="xjJIFL7i1+OOOeEyTER40wp58zTkAyY/NzW8sorMNK8=",
        public_key="dvUxLu9pLzLgE4cmB+a8GYGoNr6Z8Utoj3j7KSA7EUE=",
    )

    async with AsyncSessionContext(mock_session):
        device = await service.create_device(device_data)

        # Update with empty data (no changes)
        update_data = DeviceUpdate()
        updated_device = await service.update_device(device.id, update_data)

        # Device should remain unchanged
        assert updated_device.name == device.name
        assert updated_device.wireguard_ip == device.wireguard_ip


@pytest.mark.asyncio
async def test_update_device_same_values(
    test_network: WireGuardNetwork, test_location: Location, mock_session: AsyncSession
) -> None:
    """Test updating device with same values as current."""
    service = DeviceService(mock_session)

    device_data = DeviceCreate(
        network_id=test_network.id,
        location_id=test_location.id,
        name="test-device",
        internal_endpoint_host="192.168.1.10",
        internal_endpoint_port=51820,
        private_key="xjJIFL7i1+OOOeEyTER40wp58zTkAyY/NzW8sorMNK8=",
        public_key="dvUxLu9pLzLgE4cmB+a8GYGoNr6Z8Utoj3j7KSA7EUE=",
    )

    async with AsyncSessionContext(mock_session):
        device = await service.create_device(device_data)

        # Update with same values
        update_data = DeviceUpdate(
            name=device.name,
            wireguard_ip=device.wireguard_ip,
            public_key=device.public_key,
        )
        updated_device = await service.update_device(device.id, update_data)

        # Device should remain unchanged
        assert updated_device.name == device.name
        assert updated_device.wireguard_ip == device.wireguard_ip


@pytest.mark.asyncio
async def test_get_device_empty_network(mock_session: AsyncSession) -> None:
    """Test getting devices from an empty network."""
    service = DeviceService(mock_session)

    # Non-existent network ID
    devices = await service.get_devices_by_network("non-existent-network-id")
    assert devices == []


@pytest.mark.asyncio
async def test_available_ips_full_network(
    test_network_small: WireGuardNetwork,
    test_location_small: Location,
    mock_session: AsyncSession,
) -> None:
    """Test available IPs when network is nearly full."""
    service = DeviceService(mock_session)

    async with AsyncSessionContext(mock_session):
        # Get initial available IPs
        available_ips = await service.get_available_ips(test_network_small.id)
        initial_count = len(available_ips)

        # Create one device to consume an IP
        device_data = DeviceCreate(
            network_id=test_network_small.id,
            location_id=test_location_small.id,
            name="test-device",
            internal_endpoint_host="192.168.1.10",
            internal_endpoint_port=51820,
            private_key="xjJIFL7i1+OOOeEyTER40wp58zTkAyY/NzW8sorMNK8=",
        public_key="dvUxLu9pLzLgE4cmB+a8GYGoNr6Z8Utoj3j7KSA7EUE=",
        )
        await service.create_device(device_data)

        # Available IPs should be reduced
        new_available_ips = await service.get_available_ips(test_network_small.id)
        assert len(new_available_ips) == initial_count - 1


@pytest.mark.asyncio
async def test_update_device_clear_ip(
    test_network: WireGuardNetwork, test_location: Location, mock_session: AsyncSession
) -> None:
    """Test updating device to clear IP address."""
    service = DeviceService(mock_session)

    device_data = DeviceCreate(
        network_id=test_network.id,
        location_id=test_location.id,
        name="test-device",
        wireguard_ip="10.0.0.100",
        internal_endpoint_host="192.168.1.10",
        internal_endpoint_port=51820,
        private_key="xjJIFL7i1+OOOeEyTER40wp58zTkAyY/NzW8sorMNK8=",
        public_key="dvUxLu9pLzLgE4cmB+a8GYGoNr6Z8Utoj3j7KSA7EUE=",
    )

    async with AsyncSessionContext(mock_session):
        device = await service.create_device(device_data)

        # Clear IP by setting to None
        update_data = DeviceUpdate(wireguard_ip=None)
        updated_device = await service.update_device(device.id, update_data)

        # IP should be cleared
        assert updated_device.wireguard_ip is None


@pytest.mark.asyncio
async def test_get_nonexistent_network(mock_session: AsyncSession) -> None:
    """Test getting a non-existent network."""
    service = DeviceService(mock_session)

    with pytest.raises(ResourceNotFoundError, match="Network with ID .* not found"):
        await service._get_network("non-existent-network-id")


@pytest.mark.asyncio
async def test_device_location_validation_edge_cases(
    test_network: WireGuardNetwork, mock_session: AsyncSession
) -> None:
    """Test location validation with edge cases."""
    service = DeviceService(mock_session)

    async with AsyncSessionContext(mock_session):
        # Test with empty location ID
        with pytest.raises(ResourceNotFoundError, match="Location with ID .* not found"):
            await service._validate_location_belongs_to_network("", test_network.id)
