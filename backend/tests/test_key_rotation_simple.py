"""Tests for key rotation functionality."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from app.database.models import Device, WireGuardNetwork
from app.services.key_rotation import KeyRotationService
from app.utils.key_management import (
    decrypt_device_dek_from_json,
    decrypt_private_key_with_dek,
    encrypt_device_dek_with_api_key,
    encrypt_device_dek_with_master,
    encrypt_preshared_key,
    encrypt_private_key_with_dek,
    generate_device_dek,
)

if TYPE_CHECKING:
    from httpx import AsyncClient

VALID_PRIVATE_KEY = "YNPHguC6xJ++4Wk8YQOLYgB9p6bZq3v55y9OWVlzP3M="
VALID_PRIVATE_KEY_ALT = "4O5JUKqxp9SowOHvkkpUKv9slUc5QZwOxG5GTFdz7Xg="
VALID_PRESHARED_KEY = "8aKEwx1CnuBlX7gqCVqTlhOfwAIqSUAhVMZV9lJrM3M="


class TestKeyRotationService:
    """Test the KeyRotationService."""

    @pytest.mark.asyncio
    async def test_validate_current_password_no_networks(self, db_session):
        """Test validation when no networks exist."""
        service = KeyRotationService(db_session)

        # No networks means password is vacuously valid
        is_valid = await service.validate_current_password("any_password")
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_get_rotation_estimate_empty(self, db_session):
        """Test getting rotation estimate with no networks or devices."""
        service = KeyRotationService(db_session)

        estimate = await service.get_rotation_estimate()

        assert estimate["total_networks"] == 0
        assert estimate["total_devices"] == 0
        assert estimate["total_keys"] == 0

    @pytest.mark.asyncio
    async def test_get_rotation_estimate_with_data(
        self, db_session, test_network, test_device
    ):
        """Test getting rotation estimate with existing data."""
        service = KeyRotationService(db_session)

        estimate = await service.get_rotation_estimate()

        assert estimate["total_networks"] == 0
        assert estimate["total_devices"] == 1
        assert estimate["total_keys"] == 2

    @pytest.mark.asyncio
    async def test_validate_current_password_success(self, db_session):
        """Test successful validation of current master password."""
        network = WireGuardNetwork(
            name="Test Network",
            description="A test network",
            network_cidr="10.0.0.0/24",
        )
        db_session.add(network)
        await db_session.flush()

        device_dek = generate_device_dek()
        device = Device(
            network_id=network.id,
            location_id="test_location_id",
            name="Test Device",
            wireguard_ip="10.0.0.2",
            private_key_encrypted=encrypt_private_key_with_dek(
                VALID_PRIVATE_KEY, device_dek
            ),
            device_dek_encrypted_master=encrypt_device_dek_with_master(
                device_dek, "test_master_password"
            ),
            public_key="YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=",
        )
        db_session.add(device)
        await db_session.commit()

        service = KeyRotationService(db_session)
        is_valid = await service.validate_current_password("test_master_password")
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_current_password_failure(self, db_session):
        """Test failed validation of current master password."""
        network = WireGuardNetwork(
            name="Test Network",
            description="A test network",
            network_cidr="10.0.0.0/24",
        )
        db_session.add(network)
        await db_session.flush()

        device_dek = generate_device_dek()
        device = Device(
            network_id=network.id,
            location_id="test_location_id",
            name="Test Device",
            wireguard_ip="10.0.0.3",
            private_key_encrypted=encrypt_private_key_with_dek(
                VALID_PRIVATE_KEY, device_dek
            ),
            device_dek_encrypted_master=encrypt_device_dek_with_master(
                device_dek, "correct_password"
            ),
            public_key="YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=",
        )
        db_session.add(device)
        await db_session.commit()

        service = KeyRotationService(db_session)
        is_valid = await service.validate_current_password("wrong_password")
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_rotate_master_password_success(self, db_session):
        """Test successful master password rotation."""
        # Create a network (no key for mesh topology)
        network = WireGuardNetwork(
            name="Test Network",
            description="A test network",
            network_cidr="10.0.0.0/24",
        )
        db_session.add(network)
        await db_session.flush()

        device_dek = generate_device_dek()
        device = Device(
            network_id=network.id,
            location_id="test_location_id",
            name="Test Device",
            wireguard_ip="10.0.0.6",
            private_key_encrypted=encrypt_private_key_with_dek(
                VALID_PRIVATE_KEY_ALT, device_dek
            ),
            device_dek_encrypted_master=encrypt_device_dek_with_master(
                device_dek, "current_password"
            ),
            public_key="xTAYI66JYdM5GqYCjMRIZKNkUInjJRgHiyqfl7t80lw=",
        )
        db_session.add(device)
        await db_session.commit()

        original_device_key = device.private_key_encrypted
        original_device_dek = device.device_dek_encrypted_master

        service = KeyRotationService(db_session)

        result = await service.rotate_master_password(
            "current_password", "new_password"
        )

        assert result.total_networks == 1  # One network exists (without PSK)
        assert result.total_devices == 1
        assert result.rotated_networks == 0  # No network PSK to rotate
        assert result.rotated_devices == 1
        assert result.failed_networks == 0
        assert result.failed_devices == 0
        assert len(result.errors) == 0

        await db_session.refresh(device)

        assert device.private_key_encrypted == original_device_key
        assert device.device_dek_encrypted_master != original_device_dek

        rotated_dek = decrypt_device_dek_from_json(
            device.device_dek_encrypted_master, "new_password"
        )
        decrypted_device_key = decrypt_private_key_with_dek(
            device.private_key_encrypted, rotated_dek
        )

        assert len(decrypted_device_key) == 44

    @pytest.mark.asyncio
    async def test_rotate_master_password_invalid_current_password(self, db_session):
        """Test master password rotation with invalid current password."""
        # Create a network (no key for mesh topology)
        network = WireGuardNetwork(
            name="Test Network",
            description="A test network",
            network_cidr="10.0.0.0/24",
        )
        db_session.add(network)
        await db_session.flush()

        # Create a device with known password
        device_dek = generate_device_dek()
        device = Device(
            network_id=network.id,
            location_id="test_location_id",
            name="Test Device",
            wireguard_ip="10.0.0.4",
            private_key_encrypted=encrypt_private_key_with_dek(
                VALID_PRIVATE_KEY, device_dek
            ),
            device_dek_encrypted_master=encrypt_device_dek_with_master(
                device_dek, "correct_password"
            ),
            public_key="YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=",
        )
        db_session.add(device)
        await db_session.commit()

        service = KeyRotationService(db_session)

        with pytest.raises(ValueError, match="Invalid current master password"):
            await service.rotate_master_password("wrong_password", "new_password")

    @pytest.mark.asyncio
    async def test_rotate_master_password_with_preshared_key(self, db_session):
        """Test master password rotation with device that has preshared key."""
        # Create a network (no key for mesh topology)
        network = WireGuardNetwork(
            name="Test Network",
            description="A test network",
            network_cidr="10.0.0.0/24",
        )
        db_session.add(network)
        await db_session.flush()

        device_dek = generate_device_dek()
        device = Device(
            network_id=network.id,
            location_id="test_location_id",
            name="Test Device",
            description="A test device",
            wireguard_ip="10.0.0.5",
            private_key_encrypted=encrypt_private_key_with_dek(
                VALID_PRIVATE_KEY_ALT, device_dek
            ),
            device_dek_encrypted_master=encrypt_device_dek_with_master(
                device_dek, "current_password"
            ),
            public_key="xTAYI66JYdM5GqYCjMRIZKNkUInjJRgHiyqfl7t80lw=",
            preshared_key_encrypted=encrypt_preshared_key(
                VALID_PRESHARED_KEY, "current_password"
            ),
        )
        db_session.add(device)
        await db_session.commit()

        original_device_key = device.private_key_encrypted
        original_preshared_key = device.preshared_key_encrypted
        original_device_dek = device.device_dek_encrypted_master

        service = KeyRotationService(db_session)

        result = await service.rotate_master_password(
            "current_password", "new_password"
        )

        assert result.rotated_devices == 1
        assert result.failed_devices == 0

        await db_session.refresh(device)

        assert device.private_key_encrypted == original_device_key
        assert device.device_dek_encrypted_master != original_device_dek
        assert device.preshared_key_encrypted != original_preshared_key

        from app.utils.key_management import decrypt_preshared_key_from_json

        rotated_dek = decrypt_device_dek_from_json(
            device.device_dek_encrypted_master, "new_password"
        )
        decrypted_private_key = decrypt_private_key_with_dek(
            device.private_key_encrypted, rotated_dek
        )
        decrypted_preshared_key = decrypt_preshared_key_from_json(
            device.preshared_key_encrypted, "new_password"
        )

        assert len(decrypted_private_key) == 44
        assert len(decrypted_preshared_key) == 44

    @pytest.mark.asyncio
    async def test_rotate_master_password_preserves_api_key_dek(self, db_session):
        """Test API key wrapped DEKs remain valid after master rotation."""
        network = WireGuardNetwork(
            name="Test Network",
            description="A test network",
            network_cidr="10.0.0.0/24",
        )
        db_session.add(network)
        await db_session.flush()

        device_dek = generate_device_dek()
        api_key = "device_api_key"  # pragma: allowlist secret
        device = Device(
            network_id=network.id,
            location_id="test_location_id",
            name="Test Device",
            wireguard_ip="10.0.0.7",
            private_key_encrypted=encrypt_private_key_with_dek(
                VALID_PRIVATE_KEY, device_dek
            ),
            device_dek_encrypted_master=encrypt_device_dek_with_master(
                device_dek, "current_password"
            ),
            device_dek_encrypted_api_key=encrypt_device_dek_with_api_key(
                device_dek, api_key
            ),
            public_key="xTAYI66JYdM5GqYCjMRIZKNkUInjJRgHiyqfl7t80lw=",
        )
        db_session.add(device)
        await db_session.commit()

        original_api_key_dek = device.device_dek_encrypted_api_key

        service = KeyRotationService(db_session)
        await service.rotate_master_password("current_password", "new_password")

        await db_session.refresh(device)

        assert device.device_dek_encrypted_api_key == original_api_key_dek

        decrypted_dek = decrypt_device_dek_from_json(
            device.device_dek_encrypted_api_key, api_key
        )
        decrypted_private_key = decrypt_private_key_with_dek(
            device.private_key_encrypted, decrypted_dek
        )

        assert decrypted_private_key == VALID_PRIVATE_KEY


class TestKeyRotationAPI:
    """Test the key rotation API endpoints."""

    @pytest.mark.asyncio
    async def test_get_rotation_estimate_empty(self, client: AsyncClient):
        """Test GET /key-rotation/estimate endpoint with no data."""
        response = await client.get("/api/key-rotation/estimate")

        assert response.status_code == 200
        data = response.json()
        assert data["total_networks"] == 0
        assert data["total_devices"] == 0
        assert data["total_keys"] == 0

    @pytest.mark.asyncio
    async def test_get_rotation_estimate_with_data(
        self, client: AsyncClient, test_network, test_device
    ):
        """Test GET /key-rotation/estimate endpoint with data."""
        response = await client.get("/api/key-rotation/estimate")

        assert response.status_code == 200
        data = response.json()
        assert data["total_networks"] == 0
        assert data["total_devices"] == 1
        assert data["total_keys"] == 2

    @pytest.mark.asyncio
    async def test_validate_current_password_success(self, client: AsyncClient):
        """Test POST /key-rotation/validate-current-password with valid password."""
        response = await client.post(
            "/api/key-rotation/validate-current-password",
            json={"current_password": "any_password"},  # pragma: allowlist secret
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True

    @pytest.mark.asyncio
    async def test_rotate_master_password_success(self, client: AsyncClient):
        """Test POST /key-rotation/rotate with valid data."""
        response = await client.post(
            "/api/key-rotation/rotate",
            json={
                "current_password": "test_password",  # pragma: allowlist secret
                "new_password": "new_test_password",  # pragma: allowlist secret
                "confirm_password": "new_test_password",  # pragma: allowlist secret
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_networks"] == 0
        assert data["total_devices"] == 0
        assert data["rotated_networks"] == 0
        assert data["rotated_devices"] == 0
        assert data["failed_networks"] == 0
        assert data["failed_devices"] == 0
        assert len(data["errors"]) == 0

    @pytest.mark.asyncio
    async def test_rotate_master_password_passwords_dont_match(
        self, client: AsyncClient
    ):
        """Test POST /key-rotation/rotate with non-matching new passwords."""
        response = await client.post(
            "/api/key-rotation/rotate",
            json={
                "current_password": "test_password",  # pragma: allowlist secret
                "new_password": "new_test_password",  # pragma: allowlist secret
                "confirm_password": "different_password",  # pragma: allowlist secret
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_rotate_master_password_missing_fields(self, client: AsyncClient):
        """Test POST /key-rotation/rotate with missing required fields."""
        response = await client.post(
            "/api/key-rotation/rotate",
            json={
                "current_password": "test_password",  # pragma: allowlist secret
                "new_password": "new_test_password",  # pragma: allowlist secret
                # Missing confirm_password
            },
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_rotate_master_password_empty_fields(self, client: AsyncClient):
        """Test POST /key-rotation/rotate with empty fields."""
        response = await client.post(
            "/api/key-rotation/rotate",
            json={
                "current_password": "",
                "new_password": "",
                "confirm_password": "",
            },  # pragma: allowlist secret
        )

        assert response.status_code == 422  # Validation error
