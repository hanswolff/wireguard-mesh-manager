"""Tests for trusted proxy functionality."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers.devices import get_audit_service, get_device_config_service
from app.routers.utils import _parse_trusted_proxies
from app.schemas.device_config import DeviceConfigResponse


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    return TestClient(app)


class TestTrustedProxy:
    """Test trusted proxy functionality."""

    def test_x_forwarded_for_ignored_when_no_trusted_proxies(
        self,
        client: TestClient,
        mock_config_service,
        mock_audit_service,
        unlocked_master_password: str,
    ) -> None:
        """Test that X-Forwarded-For is ignored when no trusted proxies are configured."""
        app.dependency_overrides[get_device_config_service] = (
            lambda: mock_config_service
        )
        app.dependency_overrides[get_audit_service] = lambda: mock_audit_service

        try:
            response = client.get(
                "/api/devices/123e4567-e89b-12d3-a456-426614174000/config",
                headers={
                    "Authorization": "Bearer test_api_key",
                    "X-Forwarded-For": "203.0.113.1, 10.0.0.1",
                },
            )

            assert response.status_code == 200

            # Should use client IP, not X-Forwarded-For
            mock_config_service.validate_device_access.assert_called_once_with(
                device_id="123e4567-e89b-12d3-a456-426614174000",
                api_key="test_api_key",  # pragma: allowlist secret
                source_ip="testclient",  # Direct client IP  # pragma: allowlist secret, not forwarded  # pragma: allowlist secret
            )

        finally:
            app.dependency_overrides.clear()

    def test_api_key_header_supported_for_device_config(
        self,
        client: TestClient,
        mock_config_service,
        mock_audit_service,
        unlocked_master_password: str,
    ) -> None:
        """Test that X-API-Key is accepted for device config authentication."""
        app.dependency_overrides[get_device_config_service] = (
            lambda: mock_config_service
        )
        app.dependency_overrides[get_audit_service] = lambda: mock_audit_service

        try:
            response = client.get(
                "/api/devices/123e4567-e89b-12d3-a456-426614174000/config",
                headers={
                    "X-API-Key": "test_api_key",
                },
            )

            assert response.status_code == 200

            mock_config_service.validate_device_access.assert_called_once_with(
                device_id="123e4567-e89b-12d3-a456-426614174000",
                api_key="test_api_key",  # pragma: allowlist secret
                source_ip="testclient",  # pragma: allowlist secret
            )

        finally:
            app.dependency_overrides.clear()

    @pytest.mark.parametrize("trusted_proxy_ip", ["127.0.0.1", "127.0.0.0/8"])
    def test_x_forwarded_for_used_when_trusted_proxy(
        self,
        client: TestClient,
        mock_config_service,
        mock_audit_service,
        trusted_proxy_ip: str,
        unlocked_master_password: str,
    ) -> None:
        """Test that X-Forwarded-For is used when request comes from trusted proxy."""
        # Set trusted proxy configuration
        app.dependency_overrides[get_device_config_service] = (
            lambda: mock_config_service
        )
        app.dependency_overrides[get_audit_service] = lambda: mock_audit_service

        # Mock the settings to include trusted proxy
        from app.config import settings

        original_trusted_proxies = settings.trusted_proxies

        try:
            settings.trusted_proxies = trusted_proxy_ip
            _parse_trusted_proxies.cache_clear()

            response = client.get(
                "/api/devices/123e4567-e89b-12d3-a456-426614174000/config",
                headers={
                    "Authorization": "Bearer test_api_key",
                    "X-Forwarded-For": "203.0.113.1, 10.0.0.1",
                },
            )

            assert response.status_code == 200

            # Should use the first IP from X-Forwarded-For since client is trusted
            mock_config_service.validate_device_access.assert_called_once_with(
                device_id="123e4567-e89b-12d3-a456-426614174000",
                api_key="test_api_key",  # pragma: allowlist secret
                source_ip="203.0.113.1",  # First IP from X-Forwarded-For
            )

        finally:
            settings.trusted_proxies = original_trusted_proxies
            _parse_trusted_proxies.cache_clear()
            app.dependency_overrides.clear()

    def test_x_forwarded_for_ignored_from_untrusted_proxy(
        self,
        client: TestClient,
        mock_config_service,
        mock_audit_service,
        unlocked_master_password: str,
    ) -> None:
        """Test that X-Forwarded-For is ignored when request comes from untrusted proxy."""
        # Set trusted proxy configuration to a different IP
        app.dependency_overrides[get_device_config_service] = (
            lambda: mock_config_service
        )
        app.dependency_overrides[get_audit_service] = lambda: mock_audit_service

        from app.config import settings

        original_trusted_proxies = settings.trusted_proxies

        try:
            settings.trusted_proxies = "192.168.1.100"  # Different from test client

            response = client.get(
                "/api/devices/123e4567-e89b-12d3-a456-426614174000/config",
                headers={
                    "Authorization": "Bearer test_api_key",
                    "X-Forwarded-For": "203.0.113.1, 10.0.0.1",
                },
            )

            assert response.status_code == 200

            # Should use client IP, not X-Forwarded-For since client is not trusted
            mock_config_service.validate_device_access.assert_called_once_with(
                device_id="123e4567-e89b-12d3-a456-426614174000",
                api_key="test_api_key",  # pragma: allowlist secret
                source_ip="testclient",  # Direct client IP  # pragma: allowlist secret
            )

        finally:
            settings.trusted_proxies = original_trusted_proxies
            _parse_trusted_proxies.cache_clear()
            app.dependency_overrides.clear()

    def test_multiple_x_forwarded_for_ips_with_trusted_proxy(
        self,
        client: TestClient,
        mock_config_service,
        mock_audit_service,
        unlocked_master_password: str,
    ) -> None:
        """Test that first IP from X-Forwarded-For is used with trusted proxy."""
        app.dependency_overrides[get_device_config_service] = (
            lambda: mock_config_service
        )
        app.dependency_overrides[get_audit_service] = lambda: mock_audit_service

        from app.config import settings

        original_trusted_proxies = settings.trusted_proxies

        try:
            settings.trusted_proxies = (
                "127.0.0.1"  # pragma: allowlist secret  # pragma: allowlist secret
            )

            response = client.get(
                "/api/devices/123e4567-e89b-12d3-a456-426614174000/config",
                headers={
                    "Authorization": "Bearer test_api_key",
                    "X-Forwarded-For": "203.0.113.1, 192.168.1.1, 10.0.0.1",
                },
            )

            assert response.status_code == 200

            # Should use the first IP (original client)
            mock_config_service.validate_device_access.assert_called_once_with(
                device_id="123e4567-e89b-12d3-a456-426614174000",
                api_key="test_api_key",  # pragma: allowlist secret
                source_ip="203.0.113.1",  # First IP from X-Forwarded-For
            )

        finally:
            settings.trusted_proxies = original_trusted_proxies
            _parse_trusted_proxies.cache_clear()
            app.dependency_overrides.clear()

    def test_x_forwarded_for_with_whitespace_handling(
        self,
        client: TestClient,
        mock_config_service,
        mock_audit_service,
        unlocked_master_password: str,
    ) -> None:
        """Test that whitespace in X-Forwarded-For is handled correctly."""
        app.dependency_overrides[get_device_config_service] = (
            lambda: mock_config_service
        )
        app.dependency_overrides[get_audit_service] = lambda: mock_audit_service

        from app.config import settings

        original_trusted_proxies = settings.trusted_proxies

        try:
            settings.trusted_proxies = "127.0.0.1"  # pragma: allowlist secret

            response = client.get(
                "/api/devices/123e4567-e89b-12d3-a456-426614174000/config",
                headers={
                    "Authorization": "Bearer test_api_key",
                    "X-Forwarded-For": " 203.0.113.1 , 192.168.1.1 ",
                },
            )

            assert response.status_code == 200

            # Should use the first IP, whitespace stripped
            mock_config_service.validate_device_access.assert_called_once_with(
                device_id="123e4567-e89b-12d3-a456-426614174000",
                api_key="test_api_key",  # pragma: allowlist secret
                source_ip="203.0.113.1",  # Whitespace stripped
            )

        finally:
            settings.trusted_proxies = original_trusted_proxies
            _parse_trusted_proxies.cache_clear()
            app.dependency_overrides.clear()

    def test_client_actor_uses_correct_ip(
        self,
        client: TestClient,
        mock_config_service,
        mock_audit_service,
        unlocked_master_password: str,
    ) -> None:
        """Test that client actor identification uses the correct IP based on trusted proxy."""
        app.dependency_overrides[get_device_config_service] = (
            lambda: mock_config_service
        )
        app.dependency_overrides[get_audit_service] = lambda: mock_audit_service

        from app.config import settings

        original_trusted_proxies = settings.trusted_proxies

        try:
            settings.trusted_proxies = "127.0.0.1"  # pragma: allowlist secret

            response = client.get(
                "/api/devices/123e4567-e89b-12d3-a456-426614174000/config",
                headers={
                    "Authorization": "Bearer test_api_key",
                    "X-Forwarded-For": "203.0.113.1",
                },
            )

            assert response.status_code == 200

            # Verify the audit log uses the forwarded IP in actor
            mock_audit_service.log_event.assert_called_once()
            call_args = mock_audit_service.log_event.call_args
            assert call_args[1]["actor"] == "ip:203.0.113.1"

        finally:
            settings.trusted_proxies = original_trusted_proxies
            _parse_trusted_proxies.cache_clear()
            app.dependency_overrides.clear()


@pytest.fixture
def mock_config_service(mock_device):
    """Mock device config service."""
    from unittest.mock import Mock

    mock_service = AsyncMock()

    # Create a proper mock device object with attributes
    mock_device_obj = Mock()
    for key, value in mock_device.items():
        setattr(mock_device_obj, key, value)

    matching_key = MagicMock()
    mock_service.validate_device_access.return_value = (
        mock_device_obj,
        matching_key,
        True,
        None,
    )
    mock_service.decrypt_device_dek_with_api_key = AsyncMock(
        return_value="mock-device-dek"
    )
    mock_service.decrypt_device_private_key_with_dek = AsyncMock(
        return_value="mock-device-private-key"
    )
    mock_service.generate_device_config.return_value = DeviceConfigResponse(
        device_id="123e4567-e89b-12d3-a456-426614174000",
        device_name="Test Device",
        network_name="Test Network",
        configuration="[Interface]\nPrivateKey = mock-device-private-key\n",
        format="wg",
        created_at="2024-01-01T12:00:00Z",
    )
    return mock_service


@pytest.fixture
def mock_audit_service():
    """Mock audit service."""
    mock_service = AsyncMock()
    mock_service.log_event.return_value = None
    return mock_service


@pytest.fixture
def mock_device():
    """Mock device data."""
    return {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "name": "Test Device",
        "enabled": True,
        "network_id": "456e7890-e89b-12d3-a456-426614174000",
        "location_id": "789e0123-e89b-12d3-a456-426614174000",
        "wireguard_ip": "10.0.0.2",
        "public_key": "test_public_key",
        "preshared_key_encrypted": None,
        "created_at": "2024-01-01T12:00:00Z",
        "updated_at": "2024-01-01T12:00:00Z",
        "network": MagicMock(
            id="456e7890-e89b-12d3-a456-426614174000",
            name="Test Network",
        ),
        "location": MagicMock(
            id="789e0123-e89b-12d3-a456-426614174000",
            name="Test Location",
        ),
        "api_keys": [],
    }
