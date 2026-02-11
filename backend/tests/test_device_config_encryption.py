"""Integration tests for DeviceConfigService encryption/decryption."""

import base64
from unittest.mock import AsyncMock

import pytest

from app.database.models import Device, Location, WireGuardNetwork
from app.services.device_config import DeviceConfigService
from app.utils.key_management import encrypt_preshared_key, encrypt_private_key


def generate_test_key_bytes(seed: str = "test") -> str:
    """Generate a valid 32-byte WireGuard key for testing."""
    # Create exactly 32 bytes using the seed, padded with nulls if needed
    seed_bytes = seed.encode()
    if len(seed_bytes) > 32:
        seed_bytes = seed_bytes[:32]
    elif len(seed_bytes) < 32:
        seed_bytes = seed_bytes + b"\x00" * (32 - len(seed_bytes))
    return base64.b64encode(seed_bytes).decode()


class TestDeviceConfigServiceEncryption:
    """Test DeviceConfigService private key decryption."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = AsyncMock()
        result = AsyncMock()
        result.scalars.return_value.all.return_value = []
        db.execute.return_value = result
        return db

    @pytest.fixture
    def device_config_service(self, mock_db):
        """Create DeviceConfigService instance with mock DB."""
        return DeviceConfigService(mock_db)

    @pytest.fixture
    def sample_device(self):
        """Create a sample device with encrypted keys."""
        # Generate test WireGuard keys
        private_key = generate_test_key_bytes("device_private_key_test")
        # For public key, we need to compute it from private key in real implementation
        # For tests, we'll just use a dummy 44-character base64 string
        public_key = (
            "Lix7QPTWMuvDgMu+jh5u6n4wGJQRHLnQJAfGwJ0q2HM="  # pragma: allowlist secret
        )
        preshared_key = generate_test_key_bytes("device_preshared_key_test")

        master_password = "test_master_password_123"  # pragma: allowlist secret

        # Encrypt keys
        encrypted_private = encrypt_private_key(private_key, master_password)
        encrypted_preshared = encrypt_preshared_key(preshared_key, master_password)

        # Create device mock
        device = Device(
            id="device-123",
            name="Test Device",
            description="Test device for encryption",
            wireguard_ip="10.0.0.2",
            public_key=public_key,
            private_key_encrypted=encrypted_private,
            preshared_key_encrypted=encrypted_preshared,
            enabled=True,
            network_id="network-123",
            location_id="location-123",
        )

        return device, master_password, private_key, preshared_key

    @pytest.mark.asyncio
    async def test_decrypt_device_private_key_success(
        self, device_config_service, sample_device
    ):
        """Test successful device private key decryption."""
        device, master_password, original_private_key, _ = sample_device

        decrypted_key = await device_config_service.decrypt_device_private_key(
            device, master_password
        )

        assert decrypted_key == original_private_key

    @pytest.mark.asyncio
    async def test_decrypt_device_private_key_wrong_password(
        self, device_config_service, sample_device
    ):
        """Test device private key decryption with wrong password."""
        device, _, _, _ = sample_device
        wrong_password = "wrong_password"  # pragma: allowlist secret

        with pytest.raises(ValueError, match="Invalid master password"):
            await device_config_service.decrypt_device_private_key(
                device, wrong_password
            )

    @pytest.mark.asyncio
    async def test_decrypt_device_private_key_no_key(self, device_config_service):
        """Test decryption when device has no encrypted private key."""
        device = Device(
            id="device-456",
            name="Empty Device",
            wireguard_ip="10.0.0.3",
            public_key="Lix7QPTWMuvDgMu+jh5u6n4wGJQRHLnQJAfGwJ0q2HM=",
            private_key_encrypted="",
            network_id="network-123",
            location_id="location-123",
        )

        with pytest.raises(ValueError, match="Device has no encrypted private key"):
            await device_config_service.decrypt_device_private_key(device, "password")

    @pytest.mark.asyncio
    async def test_decrypt_preshared_key_success(
        self, device_config_service, sample_device
    ):
        """Test successful preshared key decryption."""
        device, master_password, _, original_preshared_key = sample_device

        decrypted_key = await device_config_service.decrypt_preshared_key(
            device, master_password
        )

        assert decrypted_key == original_preshared_key

    @pytest.mark.asyncio
    async def test_decrypt_preshared_key_none(self, device_config_service):
        """Test preshared key decryption when no key is set."""
        device = Device(
            id="device-789",
            name="No PSK Device",
            wireguard_ip="10.0.0.4",
            public_key="Lix7QPTWMuvDgMu+jh5u6n4wGJQRHLnQJAfGwJ0q2HM=",
            private_key_encrypted=encrypt_private_key(
                generate_test_key_bytes("no_psk_device"), "password"
            ),
            preshared_key_encrypted=None,
            network_id="network-123",
            location_id="location-123",
        )

        decrypted_key = await device_config_service.decrypt_preshared_key(
            device, "password"
        )

        assert decrypted_key is None

    @pytest.mark.asyncio
    async def test_decrypt_preshared_key_wrong_password(
        self, device_config_service, sample_device
    ):
        """Test preshared key decryption with wrong password."""
        device, _, _, _ = sample_device
        wrong_password = "wrong_password"  # pragma: allowlist secret

        with pytest.raises(ValueError, match="Invalid master password"):
            await device_config_service.decrypt_preshared_key(device, wrong_password)

    @pytest.mark.asyncio
    async def test_corrupted_encrypted_data(self, device_config_service):
        """Test decryption with corrupted encrypted data."""
        device = Device(
            id="device-corrupted",
            name="Corrupted Device",
            wireguard_ip="10.0.0.5",
            public_key="Lix7QPTWMuvDgMu+jh5u6n4wGJQRHLnQJAfGwJ0q2HM=",
            private_key_encrypted='{"encrypted": true, "corrupted": "data"}',
            network_id="network-123",
            location_id="location-123",
        )

        with pytest.raises(ValueError, match="Invalid master password"):
            await device_config_service.decrypt_device_private_key(device, "password")

    @pytest.mark.asyncio
    async def test_generate_device_config_with_decryption(
        self, device_config_service, sample_device, unlocked_master_password
    ):
        """Test generating device config with decrypted private key."""
        device, master_password, private_key, preshared_key = sample_device

        # Mock network and location relationships
        network = WireGuardNetwork(
            id="network-123",
            name="Test Network",
            network_cidr="10.0.0.0/24",
            public_key="network_public_key",
            private_key_encrypted="dummy",  # pragma: allowlist secret
        )

        location = Location(
            id="location-123",
            name="Test Location",
            external_endpoint="example.com:51820",
            network_id="network-123",
        )

        device.network = network
        device.location = location

        # Decrypt private key first
        decrypted_private_key = await device_config_service.decrypt_device_private_key(
            device, master_password
        )

        # Generate config
        config = await device_config_service.generate_device_config(
            device, decrypted_private_key, format_type="json"
        )

        assert config.device_id == device.id
        assert config.device_name == device.name
        assert config.format == "json"
        assert config.configuration is not None
