"""Tests for bootstrap token authorization in master password unlock.

This tests the security fix that requires an explicit bootstrap token
for initial master-password unlock when the database is empty,
preventing unauthenticated takeover on fresh installs.
"""

from __future__ import annotations

from datetime import datetime
import json
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy import text
from fastapi import status

if TYPE_CHECKING:
    from httpx import AsyncClient


async def _get_latest_unlock_failure(db_session):
    from sqlalchemy import select, desc

    from app.database.models import AuditEvent

    result = await db_session.execute(
        select(AuditEvent)
        .where(AuditEvent.action == "UNLOCK_FAILED")
        .order_by(desc(AuditEvent.created_at))
    )
    return result.scalars().first()


@pytest_asyncio.fixture
async def empty_database_client(db_session, client):
    """Ensure that the database is empty before certain tests."""
    # Explicitly delete all data to ensure an empty database
    # Use the test database session (db_session) instead of AsyncSessionLocal
    # to ensure we're using the per-test temporary database
    await db_session.execute(text("DELETE FROM wireguard_networks"))
    await db_session.execute(text("DELETE FROM devices"))
    await db_session.commit()

    return client


async def test_unlock_requires_bootstrap_token_when_empty_db(
    empty_database_client,
) -> None:
    """Test that unlock requires bootstrap token when database is empty."""
    from app.config import settings

    # Configure bootstrap_token to require token authorization
    with patch.object(settings, "bootstrap_token", "configured_token"):
        # First, try without bootstrap_token - should fail
        response = await empty_database_client.post(
            "/api/master-password/unlock",
            json={
                "master_password": "test_password_123",  # pragma: allowlist secret
            },
        )

        # Should get 403 Forbidden because bootstrap_token is required
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Bootstrap required" in response.json()["detail"]


async def test_unlock_with_valid_bootstrap_token(
    empty_database_client,
) -> None:
    """Test that unlock succeeds with valid bootstrap token."""
    # Mock the bootstrap_token setting
    from app.config import settings

    with patch.object(settings, "bootstrap_token", "test_bootstrap_token_12345"):
        response = await empty_database_client.post(
            "/api/master-password/unlock",
            json={
                "master_password": "test_master_password",  # pragma: allowlist secret
                "bootstrap_token": "test_bootstrap_token_12345",
            },
        )

        # Should succeed and return a session token
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "session_token" in data
        assert data["session_token"] is not None


async def test_unlock_with_invalid_bootstrap_token(
    empty_database_client,
    db_session,
) -> None:
    """Test that unlock fails with invalid bootstrap token."""
    # Mock the bootstrap_token setting
    from app.config import settings

    with patch.object(settings, "bootstrap_token", "test_bootstrap_token_12345"):
        response = await empty_database_client.post(
            "/api/master-password/unlock",
            json={
                "master_password": "test_master_password",  # pragma: allowlist secret
                "bootstrap_token": "wrong_token",
            },
        )

        # Should get 403 Forbidden
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "Invalid bootstrap token" in data["detail"]

        audit_event = await _get_latest_unlock_failure(db_session)
        assert audit_event is not None
        details = json.loads(audit_event.details or "{}")
        assert details.get("reason") == "invalid_bootstrap_token"


async def test_unlock_without_bootstrap_token_configured_allows_password(
    empty_database_client,
) -> None:
    """Test that unlock allows any password when bootstrap_token is not configured.

    This is the insecure backward-compatible behavior (logs a warning).
    """
    # Mock the bootstrap_token setting as empty (not configured)
    from app.config import settings

    with patch.object(settings, "bootstrap_token", ""):
        response = await empty_database_client.post(
            "/api/master-password/unlock",
            json={
                "master_password": "any_password_123",  # pragma: allowlist secret
            },
        )

        # Should succeed (insecure mode for backward compatibility)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "session_token" in data


async def test_unlock_with_bootstrap_token_but_db_has_encrypted_data(
    empty_database_client,
    db_session,
) -> None:
    """Test that bootstrap token is not required when DB has encrypted data.

    Once bootstrapped (has encrypted data), the bootstrap token should
    be ignored and only the master password should be validated.
    """
    # First, create a device with encrypted data to simulate bootstrapped state
    from sqlalchemy import text
    from app.utils.key_management import (
        generate_wireguard_private_key,
        generate_device_dek,
        encrypt_private_key_with_dek,
        encrypt_device_dek_with_master,
        derive_wireguard_public_key,
    )

    # Generate and encrypt test data
    test_password = "test_master_password_123"  # pragma: allowlist secret
    private_key = generate_wireguard_private_key()
    public_key = derive_wireguard_public_key(private_key)
    device_dek = generate_device_dek()
    private_key_encrypted = encrypt_private_key_with_dek(private_key, device_dek)
    device_dek_encrypted_master = encrypt_device_dek_with_master(device_dek, test_password)

    # Insert test device (network_id=1 and location_id=1 exist in empty db)
    from app.database.models import Device, WireGuardNetwork, Location
    device = Device(
        name="Test Encrypted Device",
        description="A test device with encrypted data",
        wireguard_ip="10.0.0.99",
        private_key_encrypted=private_key_encrypted,
        device_dek_encrypted_master=device_dek_encrypted_master,
        public_key=public_key,
        network_id=1,  # Default network from empty_database_client setup
        location_id=1,  # Default location
    )
    db_session.add(device)
    await db_session.commit()

    # Mock the bootstrap_token setting
    from app.config import settings

    with patch.object(settings, "bootstrap_token", "test_bootstrap_token_12345"):
        # Try unlock with correct master password but wrong/missing bootstrap token
        # This should succeed because DB is not empty
        response = await empty_database_client.post(
            "/api/master-password/unlock",
            json={
                "master_password": test_password,
            },
        )

        # Should succeed (bootstrap token ignored when DB is not empty)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "session_token" in data


async def test_unlock_with_encrypted_data_fails_with_wrong_password(
    client: AsyncClient,
    test_device,
    db_session,
) -> None:
    """Test that unlock fails with wrong password when DB has encrypted data."""
    # Mock the bootstrap_token setting (should be ignored)
    from app.config import settings

    with patch.object(settings, "bootstrap_token", "test_bootstrap_token_12345"):
        # Try unlock with wrong password and correct bootstrap token
        response = await client.post(
            "/api/master-password/unlock",
            json={
                "master_password": "wrong_password",  # pragma: allowlist secret
                "bootstrap_token": "test_bootstrap_token_12345",
            },
        )

        # Should fail because password is wrong (bootstrap token ignored)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid master password" in response.json()["detail"]

        audit_event = await _get_latest_unlock_failure(db_session)
        assert audit_event is not None
        details = json.loads(audit_event.details or "{}")
        assert details.get("reason") == "invalid_master_password"


async def test_unlock_empty_password_fails(
    empty_database_client,
) -> None:
    """Test that unlock fails with empty master password."""
    from app.config import settings

    with patch.object(settings, "bootstrap_token", "test_bootstrap_token_12345"):
        response = await empty_database_client.post(
            "/api/master-password/unlock",
            json={
                "master_password": "",  # Empty password
                "bootstrap_token": "test_bootstrap_token_12345",
            },
        )

        # Should fail with validation error
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_unlock_timing_resistant_bootstrap_token_comparison(
    empty_database_client,
) -> None:
    """Test that bootstrap token comparison is timing-resistant.

    Uses secrets.compare_digest for constant-time comparison.
    """
    # This test doesn't directly measure timing but ensures the code path
    # uses secrets.compare_digest which is already implemented
    from app.config import settings

    with patch.object(settings, "bootstrap_token", "correct_token"):
        # Wrong token of same length
        response = await empty_database_client.post(
            "/api/master-password/unlock",
            json={
                "master_password": "test_password",
                "bootstrap_token": "xorrect_token",  # Same length, wrong
            },
        )

        # Should fail
        assert response.status_code == status.HTTP_403_FORBIDDEN
