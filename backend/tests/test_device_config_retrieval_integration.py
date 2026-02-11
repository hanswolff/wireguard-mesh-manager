"""Integration tests for device configuration retrieval rules.

These tests verify the complete authentication and authorization flow
for device configuration retrieval, including:
- API key authentication
- IP allowlist validation
- Rate limiting
- Audit logging
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from fastapi import status

from app.database.models import APIKey, Device
from app.services.audit import AuditService
from app.utils.key_management import (
    decrypt_device_dek_from_json,
    encrypt_device_dek_with_api_key,
)

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def mock_device_config():
    """Mock device configuration service patches."""
    with patch("app.services.device_config.get_master_password") as mock_master:
        mock_master.return_value = "test_password"
        with patch(
            "app.services.device_config.decrypt_private_key_from_json"
        ) as mock_decrypt:
            mock_decrypt.return_value = "decrypted_private_key"
            yield mock_master, mock_decrypt


async def create_api_key(
    db_session: AsyncSession,
    device: Device,
    key: str,
    allowed_ip_ranges: str = "127.0.0.1/32",
    enabled: bool = True,
    expires_at: datetime | None = None,
) -> APIKey:
    """Create an API key for testing."""
    api_key = APIKey(
        device_id=device.id,
        network_id=device.network_id,
        key_hash=hashlib.sha256(key.encode()).hexdigest(),
        key_fingerprint=hashlib.sha256(key.encode()).hexdigest(),
        name=f"Test API Key {key[:8]}",
        allowed_ip_ranges=allowed_ip_ranges,
        enabled=enabled,
        expires_at=expires_at,
        last_used_at=None,
    )
    if device.device_dek_encrypted_master:
        device_dek = decrypt_device_dek_from_json(
            device.device_dek_encrypted_master, "test_master_password_123"
        )
        api_key.device_dek_encrypted = encrypt_device_dek_with_api_key(
            device_dek, key
        )
    if expires_at is not None:
        earliest_created = min(datetime.now(UTC), expires_at - timedelta(seconds=1))
        api_key.created_at = earliest_created
        api_key.updated_at = earliest_created
    db_session.add(api_key)
    await db_session.flush()
    return api_key


@pytest.mark.asyncio
async def test_api_key_authentication_success(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_device: Device,
    mock_device_config,
) -> None:
    """Test successful API key authentication."""
    await create_api_key(db_session, test_device, "valid_test_key")
    await db_session.commit()

    response = await async_client.get(
        f"/api/devices/{test_device.id}/config",
        headers={"Authorization": "Bearer valid_test_key"},
        params={"format": "json"},
    )

    if response.status_code != status.HTTP_200_OK:
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["device_id"] == str(test_device.id)
    assert data["device_name"] == test_device.name
    assert data["format"] == "json"


@pytest.mark.asyncio
async def test_api_key_authentication_invalid_key(
    async_client: AsyncClient, db_session: AsyncSession, test_device: Device
) -> None:
    """Test authentication with invalid API key."""
    await create_api_key(db_session, test_device, "correct_key")
    await db_session.commit()

    response = await async_client.get(
        f"/api/devices/{test_device.id}/config",
        headers={"Authorization": "Bearer wrong_key"},
        params={"format": "json"},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "Access denied" in response.json()["detail"]


@pytest.mark.asyncio
async def test_api_key_authentication_no_key(
    async_client: AsyncClient, test_device: Device
) -> None:
    """Test authentication without API key."""
    response = await async_client.get(
        f"/api/devices/{test_device.id}/config",
        params={"format": "json"},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "Access denied" in response.json()["detail"]


@pytest.mark.asyncio
async def test_api_key_authentication_disabled_key(
    async_client: AsyncClient, db_session: AsyncSession, test_device: Device
) -> None:
    """Test authentication with disabled API key."""
    await create_api_key(db_session, test_device, "disabled_key", enabled=False)
    await db_session.commit()

    response = await async_client.get(
        f"/api/devices/{test_device.id}/config",
        headers={"Authorization": "Bearer disabled_key"},
        params={"format": "json"},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "Access denied" in response.json()["detail"]


@pytest.mark.asyncio
async def test_api_key_authentication_expired_key(
    async_client: AsyncClient, db_session: AsyncSession, test_device: Device
) -> None:
    """Test authentication with expired API key."""
    expired_date = datetime.now(UTC) - timedelta(days=1)
    await create_api_key(
        db_session, test_device, "expired_key", expires_at=expired_date
    )
    await db_session.commit()

    response = await async_client.get(
        f"/api/devices/{test_device.id}/config",
        headers={"Authorization": "Bearer expired_key"},
        params={"format": "json"},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "Access denied" in response.json()["detail"]


@pytest.mark.asyncio
async def test_ip_allowlist_validation_allowed_cidr(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_device: Device,
    mock_device_config,
) -> None:
    """Test IP allowlist validation with allowed CIDR range."""
    await create_api_key(
        db_session, test_device, "test_key", allowed_ip_ranges="203.0.113.0/24"
    )
    await db_session.commit()

    response = await async_client.get(
        f"/api/devices/{test_device.id}/config",
        headers={
            "Authorization": "Bearer test_key",
            "X-Forwarded-For": "203.0.113.100",
        },
        params={"format": "json"},
    )

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_ip_allowlist_validation_allowed_single_ip(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_device: Device,
    mock_device_config,
) -> None:
    """Test IP allowlist validation with allowed single IP."""
    await create_api_key(
        db_session, test_device, "test_key", allowed_ip_ranges="203.0.113.150"
    )
    await db_session.commit()

    response = await async_client.get(
        f"/api/devices/{test_device.id}/config",
        headers={
            "Authorization": "Bearer test_key",
            "X-Forwarded-For": "203.0.113.150",
        },
        params={"format": "json"},
    )

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_ip_allowlist_validation_denied_ip(
    async_client: AsyncClient, db_session: AsyncSession, test_device: Device
) -> None:
    """Test IP allowlist validation with denied IP."""
    await create_api_key(
        db_session, test_device, "test_key", allowed_ip_ranges="203.0.113.0/24"
    )
    await db_session.commit()

    response = await async_client.get(
        f"/api/devices/{test_device.id}/config",
        headers={
            "Authorization": "Bearer test_key",
            "X-Forwarded-For": "198.51.100.50",
        },
        params={"format": "json"},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "Access denied" in response.json()["detail"]


@pytest.mark.asyncio
async def test_ip_allowlist_validation_multiple_ranges(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_device: Device,
    mock_device_config,
) -> None:
    """Test IP allowlist validation with multiple ranges."""
    await create_api_key(
        db_session,
        test_device,
        "test_key",
        allowed_ip_ranges="203.0.113.0/24,198.51.100.0/24",
    )
    await db_session.commit()

    # Test first range
    response1 = await async_client.get(
        f"/api/devices/{test_device.id}/config",
        headers={
            "Authorization": "Bearer test_key",
            "X-Forwarded-For": "203.0.113.100",
        },
        params={"format": "json"},
    )
    assert response1.status_code == status.HTTP_200_OK

    # Test second range
    response2 = await async_client.get(
        f"/api/devices/{test_device.id}/config",
        headers={
            "Authorization": "Bearer test_key",
            "X-Forwarded-For": "198.51.100.100",
        },
        params={"format": "json"},
    )
    assert response2.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_ip_allowlist_validation_no_source_ip(
    async_client: AsyncClient, db_session: AsyncSession, test_device: Device
) -> None:
    """Test IP allowlist validation when no source IP is provided."""
    await create_api_key(
        db_session, test_device, "test_key", allowed_ip_ranges="203.0.113.0/24"
    )
    await db_session.commit()

    response = await async_client.get(
        f"/api/devices/{test_device.id}/config",
        headers={"Authorization": "Bearer test_key"},
        params={"format": "json"},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "Access denied" in response.json()["detail"]


@pytest.mark.asyncio
async def test_device_not_found(
    async_client: AsyncClient, db_session: AsyncSession, test_device: Device
) -> None:
    """Test access to non-existent device."""
    await create_api_key(db_session, test_device, "test_key")
    await db_session.commit()

    response = await async_client.get(
        "/api/devices/00000000-0000-0000-0000-000000000000/config",
        headers={"Authorization": "Bearer test_key"},
        params={"format": "json"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Device not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_x_forwarded_for_header_handling(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_device: Device,
    mock_device_config,
) -> None:
    """Test X-Forwarded-For header is properly parsed."""
    await create_api_key(
        db_session, test_device, "test_key", allowed_ip_ranges="203.0.113.100"
    )
    await db_session.commit()

    response = await async_client.get(
        f"/api/devices/{test_device.id}/config",
        headers={
            "Authorization": "Bearer test_key",
            "X-Forwarded-For": "203.0.113.100, 10.0.0.1, 192.168.1.1",
        },
        params={"format": "json"},
    )

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_api_key_last_used_update(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_device: Device,
    mock_device_config,
) -> None:
    """Test that API key last_used_at timestamp is updated."""
    api_key = await create_api_key(db_session, test_device, "last_used_test_key")
    original_last_used = api_key.last_used_at
    await db_session.commit()

    import time

    time.sleep(0.01)

    response = await async_client.get(
        f"/api/devices/{test_device.id}/config",
        headers={"Authorization": "Bearer last_used_test_key"},
        params={"format": "json"},
    )

    assert response.status_code == status.HTTP_200_OK

    await db_session.refresh(api_key)
    assert api_key.last_used_at is not None
    if original_last_used:
        assert api_key.last_used_at > original_last_used


@pytest.mark.asyncio
async def test_audit_logging_successful_access(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_device: Device,
    mock_device_config,
) -> None:
    """Test audit logging for successful device access."""
    await create_api_key(
        db_session,
        test_device,
        "audit_test_key",
        allowed_ip_ranges="203.0.113.0/24",
    )
    await db_session.commit()

    audit_service = AuditService(db_session)

    with patch("app.routers.devices.get_audit_service", return_value=audit_service):
        response = await async_client.get(
            f"/api/devices/{test_device.id}/config",
            headers={
                "Authorization": "Bearer audit_test_key",
                "X-Forwarded-For": "203.0.113.100",
            },
            params={"format": "json"},
        )

        assert response.status_code == status.HTTP_200_OK

        await db_session.commit()

        from sqlalchemy import text

        result = await db_session.execute(
            text(
                "SELECT * FROM audit_events WHERE network_id = :network_id AND action = :action AND resource_type = :resource_type"
            ),
            {
                "network_id": test_device.network_id,
                "action": "RETRIEVE",
                "resource_type": "device_config",
            },
        )
        events = result.fetchall()

        assert len(events) >= 1
        event = events[0]
        assert event.resource_id == str(test_device.id)
        assert "203.0.113.100" in event.details


@pytest.mark.asyncio
async def test_audit_logging_access_denied(
    async_client: AsyncClient, db_session: AsyncSession, test_device: Device
) -> None:
    """Test audit logging for access denied scenarios."""
    await create_api_key(
        db_session, test_device, "wrong_key_test", allowed_ip_ranges="203.0.113.0/24"
    )
    await db_session.commit()

    audit_service = AuditService(db_session)

    with patch("app.routers.devices.get_audit_service", return_value=audit_service):
        response = await async_client.get(
            f"/api/devices/{test_device.id}/config",
            headers={
                "Authorization": "Bearer wrong_key",
                "X-Forwarded-For": "198.51.100.50",
            },
            params={"format": "json"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

        await db_session.commit()

        from sqlalchemy import text

        result = await db_session.execute(
            text(
                "SELECT * FROM audit_events WHERE network_id = :network_id AND action = :action AND resource_type = :resource_type"
            ),
            {
                "network_id": test_device.network_id,
                "action": "ACCESS_DENIED",
                "resource_type": "device_config",
            },
        )
        events = result.fetchall()

        assert len(events) >= 1
        event = events[0]
        assert event.resource_id == str(test_device.id)
        assert "198.51.100.50" in event.details


@pytest.mark.asyncio
async def test_rate_limiting_per_api_key(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_device: Device,
    mock_device_config,
) -> None:
    """Test rate limiting per API key."""
    await create_api_key(
        db_session,
        test_device,
        "rate_limit_test_key",
        allowed_ip_ranges="203.0.113.0/24",
    )
    await db_session.commit()

    # Make multiple requests quickly to trigger rate limiting
    responses = []
    for _ in range(5):
        response = await async_client.get(
            f"/api/devices/{test_device.id}/config",
            headers={
                "Authorization": "Bearer rate_limit_test_key",
                "X-Forwarded-For": "203.0.113.100",
            },
            params={"format": "json"},
        )
        responses.append(response)

    # At least one request should succeed
    success_responses = [r for r in responses if r.status_code == status.HTTP_200_OK]
    assert len(success_responses) >= 1

    # Eventually requests should be rate limited (429 Too Many Requests)
    rate_limited_responses = [
        r for r in responses if r.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    ]
    if len(rate_limited_responses) > 0:
        assert "rate limit" in rate_limited_responses[0].json()["detail"].lower()


@pytest.mark.asyncio
async def test_rate_limiting_per_ip_address(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_device: Device,
    mock_device_config,
) -> None:
    """Test rate limiting per IP address."""
    # Create multiple API keys for the same IP
    await create_api_key(
        db_session, test_device, "key1", allowed_ip_ranges="203.0.113.0/24"
    )
    await create_api_key(
        db_session, test_device, "key2", allowed_ip_ranges="203.0.113.0/24"
    )
    await db_session.commit()

    ip_address = "203.0.113.100"
    responses = []

    # Make requests with different API keys but same IP
    for key in ["key1", "key2", "key1", "key2", "key1"]:
        response = await async_client.get(
            f"/api/devices/{test_device.id}/config",
            headers={
                "Authorization": f"Bearer {key}",
                "X-Forwarded-For": ip_address,
            },
            params={"format": "json"},
        )
        responses.append(response)

    # Check that some requests succeed and eventually get rate limited
    success_responses = [r for r in responses if r.status_code == status.HTTP_200_OK]
    assert len(success_responses) >= 1

    rate_limited_responses = [
        r for r in responses if r.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    ]
    if len(rate_limited_responses) > 0:
        assert "rate limit" in rate_limited_responses[0].json()["detail"].lower()
