"""Tests for device configuration retrieval endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.routers.devices import get_audit_service, get_device_config_service
from app.schemas.device_config import DeviceConfigResponse


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_device() -> dict:
    """Mock device data."""
    return {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "name": "Test Device",
        "description": "Test device for config retrieval",
        "enabled": True,
        "network_id": "456e7890-e89b-12d3-a456-426614174000",
        "location_id": "789e0123-e89b-12d3-a456-426614174000",
        "wireguard_ip": "10.0.0.2",
        "public_key": "test_public_key",
        "preshared_key_encrypted": None,
        "created_at": "2024-01-01T12:00:00Z",
        "updated_at": "2024-01-01T12:00:00Z",
        "network": {
            "id": "456e7890-e89b-12d3-a456-426614174000",
            "name": "Test Network",
            "network_cidr": "10.0.0.0/24",
            "public_key": "test_network_public_key",
            "dns_servers": "8.8.8.8,8.8.4.4",
            "mtu": 1420,
            "persistent_keepalive": 25,
            "locations": [
                {
                    "id": "789e0123-e89b-12d3-a456-426614174000",
                    "name": "Test Location",
                    "external_endpoint": "vpn.example.com:51820",
                }
            ],
        },
        "location": {
            "id": "789e0123-e89b-12d3-a456-426614174000",
            "name": "Test Location",
            "external_endpoint": "vpn.example.com:51820",
        },
    }


@pytest.fixture
def mock_config_service(mock_device: dict) -> AsyncMock:
    """Mock device config service."""
    mock_service = AsyncMock()

    # Create a proper mock device object with attributes
    from unittest.mock import Mock

    mock_device_obj = Mock()
    for key, value in mock_device.items():
        setattr(mock_device_obj, key, value)

    matching_key = MagicMock()
    # Mock validate_device_access to return (device, matching_key, True, None)
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

    # Mock generate_device_config to return format based on input
    def mock_generate_config(
        device, device_private_key, format_type="wg", platform=None, device_dek=None
    ):
        return DeviceConfigResponse(
            device_id="123e4567-e89b-12d3-a456-426614174000",
            device_name=getattr(device, "name", "Test Device"),
            network_name=(
                getattr(device, "network", {}).get("name", "Test Network")
                if hasattr(device, "network")
                else "Test Network"
            ),
            configuration=f"""[Interface]
PrivateKey = {device_private_key}
Address = 10.0.0.2/24
DNS = 8.8.8.8,8.8.4.4

[Peer]
PublicKey = test_network_public_key
AllowedIPs = 10.0.0.0/24
Endpoint = vpn.example.com:51820
PersistentKeepalive = 25""",
            format=str(format_type),
            created_at="2024-01-01T12:00:00Z",
        )

    mock_service.generate_device_config.side_effect = mock_generate_config

    return mock_service


@pytest.fixture
def mock_audit_service() -> AsyncMock:
    """Mock audit service."""
    mock_service = AsyncMock()
    mock_service.log_event.return_value = None
    return mock_service


class TestDeviceConfigEndpoints:
    """Test device configuration endpoints."""

    def test_get_device_config_json_format(
        self,
        client: TestClient,
        mock_config_service: AsyncMock,
        mock_audit_service: AsyncMock,
        unlocked_master_password: str,
    ) -> None:
        """Test getting device configuration in JSON format."""
        # Mock the dependency injection
        app.dependency_overrides[get_device_config_service] = (
            lambda: mock_config_service
        )
        app.dependency_overrides[get_audit_service] = lambda: mock_audit_service

        try:
            response = client.get(
                "/api/devices/123e4567-e89b-12d3-a456-426614174000/config",
                params={"format": "json"},
                headers={"Authorization": "Bearer test_api_key"},
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["device_id"] == "123e4567-e89b-12d3-a456-426614174000"
            assert data["device_name"] == "Test Device"
            assert data["network_name"] == "Test Network"
            assert data["format"] == "json"

            # Verify services were called
            mock_config_service.validate_device_access.assert_called_once_with(
                device_id="123e4567-e89b-12d3-a456-426614174000",
                api_key="test_api_key",
                source_ip="testclient",
            )
            mock_config_service.generate_device_config.assert_called_once()
            mock_config_service.decrypt_device_dek_with_api_key.assert_awaited_once_with(
                mock_config_service.validate_device_access.return_value[0],
                "test_api_key",
                api_key_record=mock_config_service.validate_device_access.return_value[1],
            )
            mock_config_service.decrypt_device_private_key_with_dek.assert_awaited_once_with(
                mock_config_service.validate_device_access.return_value[0],
                "mock-device-dek",
            )
            mock_audit_service.log_event.assert_called_once()

        finally:
            app.dependency_overrides.clear()

    def test_get_device_config_wg_format(
        self,
        client: TestClient,
        mock_config_service: AsyncMock,
        mock_audit_service: AsyncMock,
        unlocked_master_password: str,
    ) -> None:
        """Test getting device configuration in WireGuard format."""
        app.dependency_overrides[get_device_config_service] = (
            lambda: mock_config_service
        )
        app.dependency_overrides[get_audit_service] = lambda: mock_audit_service

        try:
            response = client.get(
                "/api/devices/123e4567-e89b-12d3-a456-426614174000/config",
                params={"format": "wg"},
                headers={"Authorization": "Bearer test_api_key"},
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["format"] == "wg"
            assert "PrivateKey" in str(data["configuration"])

        finally:
            app.dependency_overrides.clear()

    def test_get_device_config_wg_endpoint(
        self,
        client: TestClient,
        mock_config_service: AsyncMock,
        mock_audit_service: AsyncMock,
        unlocked_master_password: str,
    ) -> None:
        """Test the dedicated WireGuard config endpoint."""
        app.dependency_overrides[get_device_config_service] = (
            lambda: mock_config_service
        )
        app.dependency_overrides[get_audit_service] = lambda: mock_audit_service

        try:
            response = client.get(
                "/api/devices/123e4567-e89b-12d3-a456-426614174000/config/wg",
                headers={"Authorization": "Bearer test_api_key"},
            )

            assert response.status_code == status.HTTP_200_OK
            assert response.headers["content-type"] == "text/plain; charset=utf-8"
            assert "content-disposition" in response.headers
            assert "[Interface]" in response.text
            assert "[Peer]" in response.text

        finally:
            app.dependency_overrides.clear()

    def test_get_device_config_mobile_format(
        self,
        client: TestClient,
        mock_config_service: AsyncMock,
        mock_audit_service: AsyncMock,
        unlocked_master_password: str,
    ) -> None:
        """Test getting device configuration in mobile format."""
        app.dependency_overrides[get_device_config_service] = (
            lambda: mock_config_service
        )
        app.dependency_overrides[get_audit_service] = lambda: mock_audit_service

        try:
            response = client.get(
                "/api/devices/123e4567-e89b-12d3-a456-426614174000/config",
                params={"format": "mobile", "platform": "ios"},
                headers={"Authorization": "Bearer test_api_key"},
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["format"] == "mobile"

        finally:
            app.dependency_overrides.clear()

    def test_get_device_config_unauthorized(
        self,
        client: TestClient,
        mock_config_service: AsyncMock,
        mock_audit_service: AsyncMock,
        mock_device: dict,
    ) -> None:
        """Test getting device config without authentication."""
        app.dependency_overrides[get_device_config_service] = (
            lambda: mock_config_service
        )
        app.dependency_overrides[get_audit_service] = lambda: mock_audit_service

        mock_config_service.validate_device_access.return_value = (
            MagicMock(**mock_device),
            None,
            False,
            "missing_api_key",
        )

        try:
            response = client.get(
                "/api/devices/123e4567-e89b-12d3-a456-426614174000/config",
            )

            assert response.status_code == status.HTTP_403_FORBIDDEN

        finally:
            app.dependency_overrides.clear()

    def test_get_device_config_device_not_found(
        self,
        client: TestClient,
        mock_config_service: AsyncMock,
        mock_audit_service: AsyncMock,
    ) -> None:
        """Test getting config for non-existent device."""
        # Mock validate_device_access to raise ValueError
        mock_config_service.validate_device_access.side_effect = ValueError(
            "Device not found"
        )

        app.dependency_overrides[get_device_config_service] = (
            lambda: mock_config_service
        )
        app.dependency_overrides[get_audit_service] = lambda: mock_audit_service

        try:
            response = client.get(
                "/api/devices/nonexistent-device/config",
                headers={"Authorization": "Bearer test_api_key"},
            )

            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "Device not found" in response.json()["detail"]

        finally:
            app.dependency_overrides.clear()

    def test_get_device_config_access_denied(
        self,
        client: TestClient,
        mock_config_service: AsyncMock,
        mock_audit_service: AsyncMock,
        mock_device: dict,
    ) -> None:
        """Test getting config when access is denied."""
        # Mock validate_device_access to return access denied
        mock_config_service.validate_device_access.return_value = (
            MagicMock(**mock_device),
            None,
            False,  # Access denied
            "invalid_api_key",
        )

        app.dependency_overrides[get_device_config_service] = (
            lambda: mock_config_service
        )
        app.dependency_overrides[get_audit_service] = lambda: mock_audit_service

        try:
            response = client.get(
                "/api/devices/123e4567-e89b-12d3-a456-426614174000/config",
                headers={"Authorization": "Bearer wrong_api_key"},
            )

            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert "Access denied" in response.json()["detail"]

            # Verify access denied was logged
            mock_audit_service.log_event.assert_called_with(
                network_id=mock_device["network_id"],
                actor="ip:testclient",
                action="ACCESS_DENIED",
                resource_type="device_config",
                resource_id=mock_device["id"],
                details={
                    "source_ip": "testclient",
                    "has_api_key": True,
                    "denied_reason": "invalid_api_key",
                },
            )

        finally:
            app.dependency_overrides.clear()

    def test_get_device_config_forwarded_for_header_ignored_by_default(
        self,
        client: TestClient,
        mock_config_service: AsyncMock,
        mock_audit_service: AsyncMock,
        unlocked_master_password: str,
    ) -> None:
        """Test that X-Forwarded-For header is ignored by default (deny-by-default)."""
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

            assert response.status_code == status.HTTP_200_OK

            # Verify the forwarded IP was ignored (deny-by-default behavior)
            mock_config_service.validate_device_access.assert_called_once_with(
                device_id="123e4567-e89b-12d3-a456-426614174000",
                api_key="test_api_key",
                source_ip="testclient",  # Direct client IP, not forwarded
            )

        finally:
            app.dependency_overrides.clear()
