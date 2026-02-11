from unittest.mock import AsyncMock, MagicMock

import pytest

from app.database.models import APIKey, Device
from app.services.device_config import DeviceConfigService


@pytest.fixture
def device_config_service() -> DeviceConfigService:
    """Create device config service with mocked DB."""
    return DeviceConfigService(AsyncMock())


@pytest.fixture
def mock_device() -> Device:
    """Return a mock device."""
    return MagicMock(spec=Device)


@pytest.fixture
def allowlisted_api_key() -> APIKey:
    """Return an API key with allowlisted IP ranges."""
    api_key = MagicMock(spec=APIKey)
    api_key.allowed_ip_ranges = "10.0.0.0/24"
    return api_key


@pytest.mark.asyncio
async def test_validate_device_access_blocks_missing_source_ip(
    device_config_service: DeviceConfigService,
    mock_device: Device,
    allowlisted_api_key: APIKey,
) -> None:
    """Ensure validation fails when allowlist is configured but no source IP is provided."""
    # pragma: allowlist secret
    device_config_service._get_device_with_keys = AsyncMock(return_value=mock_device)  # type: ignore[method-assign]
    device_config_service._find_matching_api_key = AsyncMock(  # type: ignore[method-assign]
        return_value=allowlisted_api_key
    )
    device_config_service._update_api_key_last_used = AsyncMock()  # type: ignore[method-assign]

    result = await device_config_service.validate_device_access(
        "device-id", api_key="secret", source_ip=None
    )

    assert result == (mock_device, allowlisted_api_key, False, "missing_source_ip")


@pytest.mark.asyncio
async def test_validate_device_access_blocks_invalid_source_ip(
    device_config_service: DeviceConfigService,
    mock_device: Device,
    allowlisted_api_key: APIKey,
) -> None:
    """Ensure malformed IP addresses are rejected when allowlists exist."""
    device_config_service._get_device_with_keys = AsyncMock(return_value=mock_device)  # type: ignore[method-assign]
    device_config_service._find_matching_api_key = AsyncMock(  # type: ignore[method-assign]
        return_value=allowlisted_api_key
    )
    device_config_service._update_api_key_last_used = AsyncMock()  # type: ignore[method-assign]
    device_config_service._is_ip_in_key_allowlist = MagicMock(  # type: ignore[method-assign]
        side_effect=ValueError("Invalid source IP for allowlist validation")
    )

    result = await device_config_service.validate_device_access(
        "device-id", api_key="secret", source_ip="not-an-ip"
    )

    assert result == (mock_device, allowlisted_api_key, False, "invalid_source_ip")


@pytest.mark.asyncio
async def test_validate_device_access_blocks_disallowed_ip(
    device_config_service: DeviceConfigService,
    mock_device: Device,
    allowlisted_api_key: APIKey,
) -> None:
    """Ensure addresses outside the allowlist are rejected."""
    device_config_service._get_device_with_keys = AsyncMock(return_value=mock_device)  # type: ignore[method-assign]
    device_config_service._find_matching_api_key = AsyncMock(  # type: ignore[method-assign]
        return_value=allowlisted_api_key
    )
    device_config_service._update_api_key_last_used = AsyncMock()  # type: ignore[method-assign]
    device_config_service._is_ip_in_key_allowlist = MagicMock(return_value=False)  # type: ignore[method-assign]

    result = await device_config_service.validate_device_access(
        "device-id", api_key="secret", source_ip="192.168.1.10"
    )

    assert result == (mock_device, allowlisted_api_key, False, "source_ip_not_allowed")


def test_is_ip_in_key_allowlist_requires_source_ip(
    device_config_service: DeviceConfigService, allowlisted_api_key: APIKey
) -> None:
    """Ensure missing source IP raises a validation error."""
    with pytest.raises(ValueError):
        device_config_service._is_ip_in_key_allowlist("", allowlisted_api_key)


def test_is_ip_in_key_allowlist_rejects_malformed(
    device_config_service: DeviceConfigService, allowlisted_api_key: APIKey
) -> None:
    """Ensure malformed IP addresses are rejected with explicit errors."""
    with pytest.raises(ValueError):
        device_config_service._is_ip_in_key_allowlist("not-an-ip", allowlisted_api_key)
