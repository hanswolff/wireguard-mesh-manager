"""Tests for router utility functions."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.routers.utils import get_audit_service, get_client_actor
from app.services.audit import AuditService


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Mock database session."""
    session = AsyncMock(spec=AsyncSession)
    return session


class TestGetClientActor:
    """Test cases for get_client_actor function."""

    def test_with_user_id_header(self) -> None:
        """Test getting actor - X-User-ID header is no longer supported."""
        headers = [(b"x-user-id", b"user123")]
        request = Request({"type": "http", "headers": headers})

        result = get_client_actor(request)
        # X-User-ID header is no longer used, system uses master sessions
        assert result == "ip:unknown"

    def test_with_forwarded_for_header(self) -> None:
        """Test getting actor - X-Forwarded-For header requires trusted proxy."""
        headers = [(b"x-forwarded-for", b"192.168.1.100, 10.0.0.1")]
        request = Request({"type": "http", "headers": headers})

        result = get_client_actor(request)
        # X-Forwarded-For is only trusted if direct connection is from a trusted proxy
        # In test environment with no trusted proxy config, it's not used
        assert result == "ip:unknown"

    def test_with_client_ip(self) -> None:
        """Test getting actor from client IP."""
        request = Request(
            {"type": "http", "client": ("192.168.1.50", 12345), "headers": []}
        )

        result = get_client_actor(request)
        assert result == "ip:192.168.1.50"

    def test_no_ip_available(self) -> None:
        """Test getting actor when no IP is available."""
        request = Request({"type": "http", "headers": []})

        result = get_client_actor(request)
        assert result == "ip:unknown"

    def test_user_id_takes_priority(self) -> None:
        """Test that X-User-ID header is no longer supported."""
        headers = [(b"x-user-id", b"user456"), (b"x-forwarded-for", b"10.0.0.1")]
        request = Request(
            {"type": "http", "client": ("192.168.1.50", 12345), "headers": headers}
        )

        result = get_client_actor(request)
        # X-User-ID header is no longer used, system uses master sessions
        # Without master session, falls back to client IP
        assert result == "ip:192.168.1.50"


class TestGetAuditService:
    """Test cases for get_audit_service function."""

    def test_returns_audit_service_instance(self, mock_db_session: AsyncMock) -> None:
        """Test that function returns AuditService instance."""
        audit_service = get_audit_service(mock_db_session)

        assert isinstance(audit_service, AuditService)
        assert audit_service.db == mock_db_session
