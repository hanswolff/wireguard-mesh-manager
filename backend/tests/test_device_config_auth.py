"""Tests for device configuration authentication functionality."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.database.models import APIKey, Device
from app.services.device_config import DeviceConfigService


@pytest.fixture
def mock_db() -> AsyncMock:
    """Mock database session."""
    db = AsyncMock()
    result = AsyncMock()
    result.scalar_one_or_none = MagicMock(return_value=None)
    db.execute.return_value = result
    return db


@pytest.fixture
def device_config_service(mock_db: AsyncMock) -> DeviceConfigService:
    """Create device config service with mock DB."""
    return DeviceConfigService(mock_db)


@pytest.fixture
def mock_device() -> Device:
    """Create mock device with API keys."""
    device = MagicMock(spec=Device)
    device.configure_mock(
        id="123e4567-e89b-12d3-a456-426614174000",
        name="Test Device",
        enabled=True,
    )
    device.network = MagicMock()
    device.location = MagicMock()
    device.api_keys = []
    return device


def create_mock_api_key(
    key: str,
    enabled: bool = True,
    expires_at: datetime | None = None,
    allowed_ip_ranges: str = "192.168.1.0/24",
) -> APIKey:
    """Create a mock API key with proper hash."""
    api_key = MagicMock(spec=APIKey)
    api_key.enabled = enabled
    api_key.key_hash = hashlib.sha256(key.encode()).hexdigest()
    api_key.key_fingerprint = None
    api_key.expires_at = expires_at
    api_key.allowed_ip_ranges = allowed_ip_ranges
    api_key.last_used_at = None
    return api_key


class TestDeviceConfigAuth:
    """Test device configuration authentication."""

    @pytest.mark.asyncio
    async def test_validate_api_key_success(
        self, device_config_service: DeviceConfigService, mock_device: Device
    ) -> None:
        """Test successful API key validation."""
        # Add valid API key to device
        valid_key = create_mock_api_key("valid_key")
        mock_device.api_keys = [valid_key]

        result = await device_config_service._validate_api_key(mock_device, "valid_key")  # type: ignore[attr-defined]
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_api_key_no_keys(
        self, device_config_service: DeviceConfigService, mock_device: Device
    ) -> None:
        """Test API key validation when device has no keys."""
        mock_device.api_keys = []

        result = await device_config_service._validate_api_key(mock_device, "any_key")  # type: ignore[attr-defined]
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_api_key_disabled(
        self, device_config_service: DeviceConfigService, mock_device: Device
    ) -> None:
        """Test API key validation with disabled key."""
        disabled_key = create_mock_api_key("disabled_key", enabled=False)
        mock_device.api_keys = [disabled_key]

        result = await device_config_service._validate_api_key(  # type: ignore[attr-defined]
            mock_device, "disabled_key"
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_api_key_expired(
        self, device_config_service: DeviceConfigService, mock_device: Device
    ) -> None:
        """Test API key validation with expired key."""
        expired_date = datetime.now(UTC) - timedelta(days=1)
        expired_key = create_mock_api_key("expired_key", expires_at=expired_date)
        mock_device.api_keys = [expired_key]

        result = await device_config_service._validate_api_key(  # type: ignore[attr-defined]
            mock_device, "expired_key"
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_api_key_invalid_hash(
        self, device_config_service: DeviceConfigService, mock_device: Device
    ) -> None:
        """Test API key validation with wrong key."""
        valid_key = create_mock_api_key("correct_key")
        mock_device.api_keys = [valid_key]

        result = await device_config_service._validate_api_key(mock_device, "wrong_key")  # type: ignore[attr-defined]
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_source_ip_allowed_cidr(
        self, device_config_service: DeviceConfigService, mock_device: Device
    ) -> None:
        """Test source IP validation with allowed CIDR range."""
        api_key = create_mock_api_key("test_key", allowed_ip_ranges="192.168.1.0/24")
        mock_device.api_keys = [api_key]

        result = await device_config_service._validate_source_ip(  # type: ignore[attr-defined]
            mock_device, "192.168.1.100"
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_source_ip_allowed_single_ip(
        self, device_config_service: DeviceConfigService, mock_device: Device
    ) -> None:
        """Test source IP validation with allowed single IP."""
        api_key = create_mock_api_key("test_key", allowed_ip_ranges="192.168.1.100")
        mock_device.api_keys = [api_key]

        result = await device_config_service._validate_source_ip(  # type: ignore[attr-defined]
            mock_device, "192.168.1.100"
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_source_ip_denied(
        self, device_config_service: DeviceConfigService, mock_device: Device
    ) -> None:
        """Test source IP validation with denied IP."""
        api_key = create_mock_api_key("test_key", allowed_ip_ranges="192.168.1.0/24")
        mock_device.api_keys = [api_key]

        result = await device_config_service._validate_source_ip(  # type: ignore[attr-defined]
            mock_device, "10.0.0.1"
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_source_ip_multiple_ranges(
        self, device_config_service: DeviceConfigService, mock_device: Device
    ) -> None:
        """Test source IP validation with multiple allowed ranges."""
        api_key = create_mock_api_key(
            "test_key", allowed_ip_ranges="192.168.1.0/24,10.0.0.0/8"
        )
        mock_device.api_keys = [api_key]

        # Test first range
        result = await device_config_service._validate_source_ip(  # type: ignore[attr-defined]
            mock_device, "192.168.1.100"
        )
        assert result is True

        # Test second range
        result = await device_config_service._validate_source_ip(  # type: ignore[attr-defined]
            mock_device, "10.0.0.1"
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_source_ip_no_keys(
        self, device_config_service: DeviceConfigService, mock_device: Device
    ) -> None:
        """Test source IP validation with no API keys."""
        mock_device.api_keys = []

        result = await device_config_service._validate_source_ip(  # type: ignore[attr-defined]
            mock_device, "192.168.1.100"
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_source_ip_invalid_ip(
        self, device_config_service: DeviceConfigService, mock_device: Device
    ) -> None:
        """Test source IP validation with invalid IP format."""
        api_key = create_mock_api_key("test_key", allowed_ip_ranges="192.168.1.0/24")
        mock_device.api_keys = [api_key]

        result = await device_config_service._validate_source_ip(  # type: ignore[attr-defined]
            mock_device, "invalid_ip"
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_source_ip_no_source_ip(
        self, device_config_service: DeviceConfigService, mock_device: Device
    ) -> None:
        """Test source IP validation with no source IP provided."""
        api_key = create_mock_api_key("test_key", allowed_ip_ranges="192.168.1.0/24")
        mock_device.api_keys = [api_key]

        result = await device_config_service._validate_source_ip(mock_device, "")  # type: ignore[attr-defined]
        assert result is False

    @pytest.mark.asyncio
    async def test_update_api_key_last_used(
        self, device_config_service: DeviceConfigService, mock_device: Device
    ) -> None:
        """Test updating API key last used timestamp."""
        api_key = create_mock_api_key("test_key")
        mock_device.api_keys = [api_key]

        await device_config_service._update_api_key_last_used(api_key)

        # Check that last_used_at was updated
        assert api_key.last_used_at is not None
        assert api_key.last_used_at > datetime.now(UTC) - timedelta(seconds=1)

    @pytest.mark.asyncio
    async def test_update_api_key_last_used_no_match(
        self, device_config_service: DeviceConfigService, mock_device: Device
    ) -> None:
        """Test updating API key last used with no matching key."""
        api_key = create_mock_api_key("test_key")
        api_key.last_used_at = None
        mock_device.api_keys = [api_key]

        await device_config_service._update_api_key_last_used(None)

        # Check that last_used_at was not updated
        assert api_key.last_used_at is None

    def test_is_api_key_valid_no_expiration(
        self, device_config_service: DeviceConfigService
    ) -> None:
        """Test API key validity check with no expiration."""
        api_key = create_mock_api_key("test_key", expires_at=None)

        result = device_config_service._is_api_key_valid(api_key)
        assert result is True

    def test_is_api_key_valid_future_expiration(
        self, device_config_service: DeviceConfigService
    ) -> None:
        """Test API key validity check with future expiration."""
        future_date = datetime.now(UTC) + timedelta(days=30)
        api_key = create_mock_api_key("test_key", expires_at=future_date)

        result = device_config_service._is_api_key_valid(api_key)
        assert result is True

    def test_is_api_key_valid_past_expiration(
        self, device_config_service: DeviceConfigService
    ) -> None:
        """Test API key validity check with past expiration."""
        past_date = datetime.now(UTC) - timedelta(days=1)
        api_key = create_mock_api_key("test_key", expires_at=past_date)

        result = device_config_service._is_api_key_valid(api_key)
        assert result is False
