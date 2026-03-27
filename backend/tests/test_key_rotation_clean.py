"""Clean tests for key rotation functionality."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import pytest_asyncio

from app.database.models import Device, Location, WireGuardNetwork
from app.services.key_rotation import KeyRotationService
from app.utils.key_management import (
    decrypt_device_dek_from_json,
    decrypt_private_key_with_dek,
    encrypt_device_dek_with_master,
    encrypt_preshared_key,
    encrypt_private_key_with_dek,
    generate_device_dek,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
async def test_network_with_key(db_session: AsyncSession) -> WireGuardNetwork:
    """Create a test network without a private key (mesh topology)."""
    network = WireGuardNetwork(
        name="Test Network",
        description="A test network",
        network_cidr="10.0.0.0/24",
    )
    db_session.add(network)
    await db_session.commit()
    await db_session.refresh(network)
    return network


@pytest_asyncio.fixture
async def test_network_mesh_topology(db_session: AsyncSession) -> WireGuardNetwork:
    """Create a test network without private key (mesh topology)."""
    network = WireGuardNetwork(
        name="Mesh Network",
        description="A mesh topology network",
        network_cidr="10.1.0.0/24",
        private_key_encrypted=None,
        public_key=None,
    )
    db_session.add(network)
    await db_session.commit()
    await db_session.refresh(network)
    return network


@pytest_asyncio.fixture
async def test_location(
    db_session: AsyncSession, test_network_with_key: WireGuardNetwork
) -> Location:
    """Create a test location."""
    location = Location(
        network_id=test_network_with_key.id,
        name="Test Location",
        description="A test location",
    )
    db_session.add(location)
    await db_session.commit()
    await db_session.refresh(location)
    return location


@pytest_asyncio.fixture
async def test_device_with_keys(
    db_session: AsyncSession,
    test_network_with_key: WireGuardNetwork,
    test_location: Location,
) -> Device:
    """Create a test device with encrypted private and preshared keys."""
    device_dek = generate_device_dek()
    device = Device(
        network_id=test_network_with_key.id,
        location_id=test_location.id,
        name="Test Device",
        description="A test device",
        wireguard_ip="10.0.0.2",
        private_key_encrypted=encrypt_private_key_with_dek(
            "4O5JUKqxp9SowOHvkkpUKv9slUc5QZwOxG5GTFdz7Xg=",  # pragma: allowlist secret
            device_dek,
        ),
        device_dek_encrypted_master=encrypt_device_dek_with_master(
            device_dek,
            "test_password",
        ),
        public_key="xTAYI66JYdM5GqYCjMRIZKNkUInjJRgHiyqfl7t80lw=",  # pragma: allowlist secret
        preshared_key_encrypted=encrypt_preshared_key(
            "8aKEwx1CnuBlX7gqCVqTlhOfwAIqSUAhVMZV9lJrM3M=",  # pragma: allowlist secret
            "test_password",
        ),
    )
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)
    return device


class TestKeyRotationService:
    """Test the KeyRotationService."""

    @pytest.mark.asyncio
    async def test_validate_current_password_no_networks(
        self, db_session: AsyncSession
    ):
        """Test validation when no networks exist."""
        service = KeyRotationService(db_session)
        is_valid = await service.validate_current_password("any_password")
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_get_rotation_estimate_empty(self, db_session: AsyncSession):
        """Test getting rotation estimate with no networks or devices."""
        service = KeyRotationService(db_session)
        estimate = await service.get_rotation_estimate()
        assert estimate["total_networks"] == 0
        assert estimate["total_devices"] == 0
        assert estimate["total_keys"] == 0

    @pytest.mark.asyncio
    async def test_get_rotation_estimate_with_data(
        self,
        db_session: AsyncSession,
        test_device_with_keys: Device,
    ):
        """Test getting rotation estimate with existing data."""
        service = KeyRotationService(db_session)
        estimate = await service.get_rotation_estimate()
        assert estimate["total_networks"] == 0
        assert estimate["total_devices"] == 1
        assert estimate["total_keys"] == 2

    @pytest.mark.asyncio
    async def test_validate_current_password_success(
        self, db_session: AsyncSession, test_device_with_keys: Device
    ):
        """Test successful validation of current master password."""
        service = KeyRotationService(db_session)
        is_valid = await service.validate_current_password("test_password")
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_current_password_failure(
        self, db_session: AsyncSession, test_device_with_keys: Device
    ):
        """Test failed validation of current master password."""
        service = KeyRotationService(db_session)
        is_valid = await service.validate_current_password("wrong_password")
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_rotate_master_password_success(
        self,
        db_session: AsyncSession,
        test_device_with_keys: Device,
    ):
        """Test successful master password rotation."""
        service = KeyRotationService(db_session)

        original_device_key = test_device_with_keys.private_key_encrypted
        original_preshared_key = test_device_with_keys.preshared_key_encrypted
        original_device_dek = test_device_with_keys.device_dek_encrypted_master

        result = await service.rotate_master_password("test_password", "new_password")

        assert result.total_networks == 1  # One network exists (without PSK)
        assert result.total_devices == 1
        assert result.rotated_networks == 0  # No network PSK to rotate
        assert result.rotated_devices == 1
        assert result.failed_networks == 0
        assert result.failed_devices == 0
        assert len(result.errors) == 0

        await db_session.refresh(test_device_with_keys)

        assert test_device_with_keys.private_key_encrypted == original_device_key
        assert test_device_with_keys.device_dek_encrypted_master != original_device_dek
        assert test_device_with_keys.preshared_key_encrypted != original_preshared_key

    @pytest.mark.asyncio
    async def test_rotate_master_password_invalid_current_password(
        self, db_session: AsyncSession, test_device_with_keys: Device
    ):
        """Test master password rotation with invalid current password."""
        service = KeyRotationService(db_session)

        with pytest.raises(ValueError, match="Invalid current master password"):
            await service.rotate_master_password("wrong_password", "new_password")

    @pytest.mark.asyncio
    async def test_validate_password_with_mesh_topology(
        self,
        db_session: AsyncSession,
        test_network_mesh_topology: WireGuardNetwork,
    ):
        """Test password validation with network without keys."""
        mesh_location = Location(
            network_id=test_network_mesh_topology.id,
            name="Mesh Location",
        )
        db_session.add(mesh_location)
        await db_session.commit()

        device_dek = generate_device_dek()
        mesh_device = Device(
            network_id=test_network_mesh_topology.id,
            location_id=mesh_location.id,
            name="Mesh Device",
            wireguard_ip="10.1.0.2",
            private_key_encrypted=encrypt_private_key_with_dek(
                "4O5JUKqxp9SowOHvkkpUKv9slUc5QZwOxG5GTFdz7Xg=",  # pragma: allowlist secret
                device_dek,
            ),
            device_dek_encrypted_master=encrypt_device_dek_with_master(
                device_dek,
                "mesh_password",
            ),
            public_key="xTAYI66JYdM5GqYCjMRIZKNkUInjJRgHiyqfl7t80lw=",  # pragma: allowlist secret
        )
        db_session.add(mesh_device)
        await db_session.commit()

        service = KeyRotationService(db_session)

        is_valid = await service.validate_current_password("mesh_password")
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_rotate_password_with_mesh_topology(
        self,
        db_session: AsyncSession,
        test_network_mesh_topology: WireGuardNetwork,
    ):
        """Test password rotation with network without keys."""
        mesh_location = Location(
            network_id=test_network_mesh_topology.id,
            name="Mesh Location",
        )
        db_session.add(mesh_location)
        await db_session.commit()

        device_dek = generate_device_dek()
        mesh_device = Device(
            network_id=test_network_mesh_topology.id,
            location_id=mesh_location.id,
            name="Mesh Device",
            wireguard_ip="10.1.0.2",
            private_key_encrypted=encrypt_private_key_with_dek(
                "4O5JUKqxp9SowOHvkkpUKv9slUc5QZwOxG5GTFdz7Xg=",  # pragma: allowlist secret
                device_dek,
            ),
            device_dek_encrypted_master=encrypt_device_dek_with_master(
                device_dek,
                "mesh_password",
            ),
            public_key="xTAYI66JYdM5GqYCjMRIZKNkUInjJRgHiyqfl7t80lw=",  # pragma: allowlist secret
        )
        db_session.add(mesh_device)
        await db_session.commit()

        original_device_key = mesh_device.private_key_encrypted

        service = KeyRotationService(db_session)

        result = await service.rotate_master_password(
            "mesh_password", "new_mesh_password"
        )

        assert result.total_networks == 1  # One network exists (without PSK)
        assert result.total_devices == 1
        assert result.rotated_networks == 0  # No network PSK to rotate
        assert result.rotated_devices == 1
        assert result.failed_networks == 0
        assert result.failed_devices == 0
        assert len(result.errors) == 0

        await db_session.refresh(mesh_device)

        assert mesh_device.private_key_encrypted == original_device_key

        rotated_dek = decrypt_device_dek_from_json(
            mesh_device.device_dek_encrypted_master, "new_mesh_password"
        )
        decrypted_private_key = decrypt_private_key_with_dek(
            mesh_device.private_key_encrypted, rotated_dek
        )

        assert len(decrypted_private_key) == 44
