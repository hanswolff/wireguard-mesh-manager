"""Tests for audit logging service."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import AuditEvent
from app.services.audit import AuditService


@pytest.fixture
def audit_service(mock_db_session: AsyncSession) -> AuditService:
    """Create audit service fixture."""
    return AuditService(mock_db_session)


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    return session


class TestAuditService:
    """Test cases for AuditService."""

    @pytest.mark.asyncio
    async def test_log_event_basic(
        self, audit_service: AuditService, mock_db_session: AsyncMock
    ) -> None:
        """Test basic event logging."""
        network_id = "test-network-id"
        actor = "test-user"
        action = "CREATE"
        resource_type = "network"
        resource_id = "test-resource-id"
        details = {"key": "value"}

        await audit_service.log_event(
            network_id=network_id,
            actor=actor,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
        )

        # Verify session.add was called
        mock_db_session.add.assert_called_once()

        # Get the audit event that was added
        call_args = mock_db_session.add.call_args[0][0]
        assert isinstance(call_args, AuditEvent)
        assert call_args.network_id == network_id
        assert call_args.actor == actor
        assert call_args.action == action
        assert call_args.resource_type == resource_type
        assert call_args.resource_id == resource_id
        assert call_args.details == json.dumps(details, separators=(",", ":"))

    @pytest.mark.asyncio
    async def test_log_event_without_details(
        self, audit_service: AuditService, mock_db_session: AsyncMock
    ) -> None:
        """Test event logging without details."""
        await audit_service.log_event(
            network_id="test-network-id",
            actor="test-user",
            action="DELETE",
            resource_type="location",
        )

        mock_db_session.add.assert_called_once()
        call_args = mock_db_session.add.call_args[0][0]
        assert isinstance(call_args, AuditEvent)
        assert call_args.details is None

    @pytest.mark.asyncio
    async def test_sanitize_details_removes_secrets(
        self, audit_service: AuditService
    ) -> None:
        """Test that sensitive information is removed from details."""
        details = {
            "name": "test-network",
            "private_key": "secret-key-123",
            "public_key": "public-key-456",
            "password": "secret-password",
            "api_key_hash": "hashed-key",
            "nested": {"token": "secret-token", "normal_field": "keep-me"},
            "list_data": [{"secret": "hidden"}, "normal-value", "private-key-value"],
        }

        sanitized = audit_service._sanitize_details(details)

        # Check that secrets are redacted
        assert sanitized["private_key"] == "[REDACTED]"  # type: ignore[index]
        assert sanitized["public_key"] == "[REDACTED]"  # type: ignore[index]
        assert sanitized["password"] == "[REDACTED]"  # type: ignore[index]
        assert sanitized["api_key_hash"] == "[REDACTED]"  # type: ignore[index]

        # Check nested structure
        assert sanitized["nested"]["token"] == "[REDACTED]"  # type: ignore[index]
        assert sanitized["nested"]["normal_field"] == "keep-me"  # type: ignore[index]

        # Check list structure
        assert sanitized["list_data"][0]["secret"] == "[REDACTED]"  # type: ignore[index]
        assert sanitized["list_data"][1] == "normal-value"  # type: ignore[index]
        assert (
            sanitized["list_data"][2] == "[REDACTED]"  # type: ignore[index]
        )  # "private-key-value" contains "private" and should be redacted

        # Check that non-sensitive fields are preserved
        assert sanitized["name"] == "test-network"  # type: ignore[index]

    @pytest.mark.asyncio
    async def test_log_api_access(
        self, audit_service: AuditService, mock_db_session: AsyncMock
    ) -> None:
        """Test API access logging."""
        network_id = "test-network-id"
        device_id = "test-device-id"
        source_ip = "192.168.1.100"

        await audit_service.log_api_access(
            network_id=network_id,
            device_id=device_id,
            source_ip=source_ip,
            action="CONFIG_RETRIEVAL",
            success=True,
        )

        mock_db_session.add.assert_called_once()
        call_args = mock_db_session.add.call_args[0][0]
        assert isinstance(call_args, AuditEvent)
        assert call_args.network_id == network_id
        assert call_args.actor == f"device:{device_id}"
        assert call_args.action == "CONFIG_RETRIEVAL"
        assert call_args.resource_type == "api_key"
        assert call_args.resource_id == device_id

        # Check details
        details = json.loads(call_args.details)  # type: ignore[arg-type]
        assert details["source_ip"] == source_ip
        assert details["success"] is True

    @pytest.mark.asyncio
    async def test_log_admin_action(
        self, audit_service: AuditService, mock_db_session: AsyncMock
    ) -> None:
        """Test admin action logging."""
        network_id = "test-network-id"
        admin_actor = "admin-user"
        action = "UPDATE"
        resource_type = "device"
        resource_id = "device-123"
        resource_name = "test-device"
        changes = {"enabled": {"old": False, "new": True}}

        await audit_service.log_admin_action(
            network_id=network_id,
            admin_actor=admin_actor,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            changes=changes,
        )

        mock_db_session.add.assert_called_once()
        call_args = mock_db_session.add.call_args[0][0]
        assert isinstance(call_args, AuditEvent)
        assert call_args.network_id == network_id
        assert call_args.actor == admin_actor
        assert call_args.action == action
        assert call_args.resource_type == resource_type
        assert call_args.resource_id == resource_id

        # Check details
        details = json.loads(call_args.details)  # type: ignore[arg-type]
        assert details["resource_name"] == resource_name
        assert details["changes"] == changes

    @pytest.mark.asyncio
    async def test_log_admin_action_minimal(
        self, audit_service: AuditService, mock_db_session: AsyncMock
    ) -> None:
        """Test admin action logging with minimal parameters."""
        await audit_service.log_admin_action(
            network_id="test-network-id",
            admin_actor="admin-user",
            action="DELETE",
            resource_type="network",
        )

        mock_db_session.add.assert_called_once()
        call_args = mock_db_session.add.call_args[0][0]
        assert isinstance(call_args, AuditEvent)
        assert call_args.actor == "admin-user"
        assert call_args.action == "DELETE"
        assert call_args.resource_type == "network"
        assert call_args.resource_id is None

        # Details should be None when no optional params provided
        assert call_args.details is None

    def test_case_insensitive_secret_detection(
        self, audit_service: AuditService
    ) -> None:
        """Test that secret detection works with different cases."""
        details = {
            "PRIVATE_KEY": "secret",
            "private_key": "secret",
            "PUBLIC_KEY": "secret",
            "api_key": "secret",
            "AUTH_TOKEN": "secret",
            "normal_field": "keep",
        }

        sanitized = audit_service._sanitize_details(details)

        assert sanitized["PRIVATE_KEY"] == "[REDACTED]"  # type: ignore[index]
        assert sanitized["private_key"] == "[REDACTED]"  # type: ignore[index]
        assert sanitized["PUBLIC_KEY"] == "[REDACTED]"  # type: ignore[index]
        assert sanitized["api_key"] == "[REDACTED]"  # type: ignore[index]
        assert sanitized["AUTH_TOKEN"] == "[REDACTED]"  # type: ignore[index]
        assert sanitized["normal_field"] == "keep"  # type: ignore[index]

    def test_empty_details_sanitization(self, audit_service: AuditService) -> None:
        """Test sanitizing empty details."""
        assert audit_service._sanitize_details({}) == {}
        assert audit_service._sanitize_details(None) is None
