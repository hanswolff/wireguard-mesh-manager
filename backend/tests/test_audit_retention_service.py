"""Tests for audit retention service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.services.audit_retention import AuditExportService, AuditRetentionService


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return AsyncMock()


@pytest.fixture
def retention_service(mock_db):
    """Create audit retention service with mock database."""
    return AuditRetentionService(mock_db)


@pytest.fixture
def export_service(mock_db):
    """Create audit export service with mock database."""
    return AuditExportService(mock_db)


class TestAuditRetentionService:
    """Test cases for AuditRetentionService."""

    async def test_get_expired_events_cutoff(self, retention_service):
        """Test getting cutoff date for expired events."""
        cutoff = await retention_service.get_expired_events_cutoff()

        # Should be retention_days ago from now (default is 365 days)
        from app.config import settings

        expected = datetime.now(UTC) - timedelta(days=settings.audit_retention_days)
        assert abs((cutoff - expected).total_seconds()) < 1

    async def test_count_expired_events(self, retention_service, mock_db):
        """Test counting expired audit events."""
        # Mock the database response
        mock_result = AsyncMock()
        mock_result.scalar.return_value = 42
        mock_db.execute.return_value = mock_result

        count = await retention_service.count_expired_events()

        assert count == 42
        mock_db.execute.assert_called_once()

    async def test_cleanup_expired_events_no_events(self, retention_service, mock_db):
        """Test cleanup when no expired events exist."""
        # Mock count to return 0
        retention_service.count_expired_events = AsyncMock(return_value=0)

        result = await retention_service.cleanup_expired_events()

        assert result["events_deleted"] == 0
        mock_db.commit.assert_not_called()

    async def test_cleanup_expired_events_with_events(self, retention_service, mock_db):
        """Test cleanup when expired events exist."""
        # Mock count to return 10
        retention_service.count_expired_events = AsyncMock(return_value=10)

        result = await retention_service.cleanup_expired_events()

        assert result["events_deleted"] == 10
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()


class TestAuditExportService:
    """Test cases for AuditExportService."""

    async def test_get_audit_statistics(self, export_service, mock_db):
        """Test getting audit statistics."""
        # Mock database responses
        mock_result_total = AsyncMock()
        mock_result_total.scalar.return_value = 100
        mock_result_recent = AsyncMock()
        mock_result_recent.scalar.return_value = 25

        mock_result_7d = AsyncMock()
        mock_result_7d.scalar.return_value = 50

        # Mock action breakdown results
        mock_result_actions = AsyncMock()
        mock_result_actions.fetchall = lambda: [("create", 50), ("update", 30), ("delete", 20)]

        mock_result_recent_actions = AsyncMock()
        mock_result_recent_actions.fetchall = lambda: [("create", 10), ("update", 5)]

        mock_result_7d_actions = AsyncMock()
        mock_result_7d_actions.fetchall = lambda: [("create", 25), ("update", 15), ("delete", 10)]

        mock_db.execute.side_effect = [
            mock_result_total,
            mock_result_recent,
            mock_result_7d,
            mock_result_actions,
            mock_result_recent_actions,
            mock_result_7d_actions,
        ]

        # Mock retention service
        with patch(
            "app.services.audit_retention.AuditRetentionService"
        ) as mock_retention:
            mock_retention_instance = AsyncMock()
            mock_retention_instance.count_expired_events.return_value = 15
            mock_retention.return_value = mock_retention_instance

            stats = await export_service.get_audit_statistics()

            assert stats["total_events"] == 100
            assert stats["recent_events_24h"] == 25
            assert stats["expired_events"] == 15
