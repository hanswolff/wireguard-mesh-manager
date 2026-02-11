"""Tests for audit event retention and export functionality."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest_asyncio
from fastapi.testclient import TestClient

from app.config import settings
from app.database.models import AuditEvent, WireGuardNetwork
from app.main import app
from app.services.audit_retention import (
    AuditExportFormat,
    AuditExportService,
    AuditRetentionService,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

client = TestClient(app)


@pytest_asyncio.fixture
async def sample_network(db_session: AsyncSession) -> WireGuardNetwork:
    """Create a sample network for testing."""
    network = WireGuardNetwork(
        name="Test Network",
        network_cidr="10.0.0.0/24",
        public_key="test_public_key",
        private_key_encrypted="encrypted_private_key",
    )
    db_session.add(network)
    await db_session.commit()
    await db_session.refresh(network)
    return network


@pytest_asyncio.fixture
async def sample_audit_events(
    db_session: AsyncSession, sample_network: WireGuardNetwork
) -> list[AuditEvent]:
    """Create sample audit events for testing."""
    events = []
    base_time = datetime.now(UTC) - timedelta(days=10)

    for i in range(20):
        event = AuditEvent(
            network_id=sample_network.id,
            actor=f"test_user_{i % 3}",
            action=["CREATE", "UPDATE", "DELETE"][i % 3],
            resource_type="device",
            resource_id=f"device_{i}",
            details=json.dumps({"test": f"data_{i}"}),
        )
        # Manually set created_at for testing
        event.created_at = base_time + timedelta(hours=i)
        events.append(event)
        db_session.add(event)

    # Add some old events beyond retention period
    old_time = datetime.now(UTC) - timedelta(days=settings.audit_retention_days + 10)
    for i in range(5):
        old_event = AuditEvent(
            network_id=sample_network.id,
            actor="old_user",
            action="CREATE",
            resource_type="device",
            resource_id=f"old_device_{i}",
        )
        # Manually set created_at for testing
        old_event.created_at = old_time + timedelta(hours=i)
        events.append(old_event)
        db_session.add(old_event)

    await db_session.commit()
    return events


class TestAuditRetentionService:
    """Tests for AuditRetentionService."""

    async def test_get_expired_events_cutoff(self, db_session: AsyncSession) -> None:
        """Test getting cutoff date for expired events."""
        service = AuditRetentionService(db_session)
        cutoff = await service.get_expired_events_cutoff()

        expected_cutoff = datetime.now(UTC) - timedelta(
            days=settings.audit_retention_days
        )
        assert (
            abs((cutoff - expected_cutoff).total_seconds()) < 60
        )  # Allow 1 minute difference

    async def test_count_expired_events(
        self, db_session: AsyncSession, sample_audit_events: list[AuditEvent]
    ) -> None:
        """Test counting expired audit events."""
        service = AuditRetentionService(db_session)
        expired_count = await service.count_expired_events()

        # Should have 5 old events beyond retention period
        assert expired_count == 5

    async def test_cleanup_expired_events(
        self, db_session: AsyncSession, sample_audit_events: list[AuditEvent]
    ) -> None:
        """Test cleaning up expired audit events."""
        service = AuditRetentionService(db_session)

        # Count events before cleanup
        from sqlalchemy import select

        all_events_stmt = select(AuditEvent)
        result = await db_session.execute(all_events_stmt)
        initial_count = len(result.scalars().all())

        # Perform cleanup
        cleanup_result = await service.cleanup_expired_events()

        # Verify cleanup results
        assert cleanup_result["events_deleted"] == 5
        assert cleanup_result["retention_days"] == settings.audit_retention_days

        # Verify events were actually deleted
        result = await db_session.execute(all_events_stmt)
        final_count = len(result.scalars().all())
        assert final_count == initial_count - 5

    async def test_cleanup_no_expired_events(self, db_session: AsyncSession) -> None:
        """Test cleanup when no expired events exist."""
        service = AuditRetentionService(db_session)

        result = await service.cleanup_expired_events()

        assert result["events_deleted"] == 0
        assert "cutoff_date" in result
        assert result["retention_days"] == settings.audit_retention_days


class TestAuditExportService:
    """Tests for AuditExportService."""

    async def test_export_all_events_json(
        self, db_session: AsyncSession, sample_audit_events: list[AuditEvent]
    ) -> None:
        """Test exporting all audit events in JSON format."""
        service = AuditExportService(db_session)

        result = await service.export_audit_events(format_type=AuditExportFormat.JSON)

        assert result["metadata"]["total_events"] == 25  # 20 recent + 5 old
        assert result["metadata"]["export_format"] == "json"
        assert len(result["events"]) == 25

        # Check event structure
        event = result["events"][0]
        assert "id" in event
        assert "network_id" in event
        assert "actor" in event
        assert "action" in event
        assert "created_at" in event

    async def test_export_events_csv(
        self, db_session: AsyncSession, sample_audit_events: list[AuditEvent]
    ) -> None:
        """Test exporting audit events in CSV format."""
        service = AuditExportService(db_session)

        result = await service.export_audit_events(format_type=AuditExportFormat.CSV)

        assert result["metadata"]["total_events"] == 25
        assert result["metadata"]["export_format"] == "csv"

        # CSV should be a string
        assert isinstance(result["events"], str)

        # Check CSV header
        lines = result["events"].strip().split("\n")
        header = lines[0]
        assert "id,network_id,network_name,actor" in header

    async def test_export_events_with_filters(
        self, db_session: AsyncSession, sample_audit_events: list[AuditEvent]
    ) -> None:
        """Test exporting audit events with filters."""
        service = AuditExportService(db_session)

        # Filter by action
        result = await service.export_audit_events(
            action_filter="CREATE", format_type=AuditExportFormat.JSON
        )

        # Should only include CREATE events
        create_events = [e for e in result["events"] if e["action"] == "CREATE"]
        assert len(create_events) == len(result["events"])
        assert all(e["action"] == "CREATE" for e in result["events"])

    async def test_export_events_date_range(
        self, db_session: AsyncSession, sample_audit_events: list[AuditEvent]
    ) -> None:
        """Test exporting audit events with date range filter."""
        service = AuditExportService(db_session)

        # Export events from 12 days ago (should include all 20 recent events, not the 5 old ones)
        start_date = datetime.now(UTC) - timedelta(days=12)
        result = await service.export_audit_events(
            start_date=start_date, format_type=AuditExportFormat.JSON
        )

        # Should include the 20 recent events but exclude the 5 very old ones
        assert result["metadata"]["total_events"] == 20

        # All events should be after start_date
        for event in result["events"]:
            event_date = datetime.fromisoformat(event["created_at"])
            assert event_date >= start_date

    async def test_export_events_exclude_details(
        self, db_session: AsyncSession, sample_audit_events: list[AuditEvent]
    ) -> None:
        """Test exporting events without details."""
        service = AuditExportService(db_session)

        result = await service.export_audit_events(
            include_details=False, format_type=AuditExportFormat.JSON
        )

        # Details should be None for all events
        for event in result["events"]:
            assert event["details"] is None

    async def test_get_audit_statistics(
        self, db_session: AsyncSession, sample_audit_events: list[AuditEvent]
    ) -> None:
        """Test getting audit statistics."""
        service = AuditExportService(db_session)

        stats = await service.get_audit_statistics()

        assert stats["total_events"] == 25
        assert stats["retention_days"] == settings.audit_retention_days
        assert stats["expired_events"] == 5
        assert "recent_events_24h" in stats
        assert "storage_stats" in stats


class TestAuditRouter:
    """Tests for audit router endpoints."""

    @patch("app.routers.audit.get_client_actor")
    @patch("app.routers.audit.get_db")
    async def test_get_audit_statistics(
        self, mock_get_db: AsyncMock, mock_get_actor: AsyncMock
    ) -> None:
        """Test getting audit statistics."""
        # Mock dependencies
        mock_get_actor.return_value = "test_user"

        mock_db = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db

        mock_service = AsyncMock()
        mock_service.get_audit_statistics.return_value = {
            "total_events": 100,
            "expired_events": 10,
            "retention_days": 365,
        }

        with patch("app.services.audit_retention.AuditExportService", return_value=mock_service):
            response = client.get("/api/audit/statistics")
            assert response.status_code == 200
            data = response.json()
            assert data["total_events"] == 100

    @patch("app.routers.audit.get_client_actor")
    @patch("app.routers.audit.get_db")
    async def test_cleanup_expired_events(
        self, mock_get_db: AsyncMock, mock_get_actor: AsyncMock
    ) -> None:
        """Test cleanup."""
        mock_get_actor.return_value = "admin_user"

        mock_db = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db

        mock_retention_service = AsyncMock()
        mock_retention_service.cleanup_expired_events.return_value = {
            "events_deleted": 5,
            "cutoff_date": "2023-01-01T00:00:00Z",
            "retention_days": 365,
        }

        mock_audit_service = AsyncMock()
        mock_audit_service.log_admin_action = AsyncMock()

        with (
            patch(
                "app.services.audit_retention.AuditRetentionService",
                return_value=mock_retention_service,
            ),
            patch("app.services.audit.AuditService", return_value=mock_audit_service),
        ):
            response = client.post("/api/audit/cleanup")
            assert response.status_code == 200
            data = response.json()
            assert data["events_deleted"] == 5

    @patch("app.routers.audit.get_client_actor")
    @patch("app.routers.audit.get_db")
    async def test_export_audit_events_invalid_format(
        self, mock_get_db: AsyncMock, mock_get_actor: AsyncMock
    ) -> None:
        """Test export with invalid format."""
        mock_get_actor.return_value = "test_user"
        mock_get_db.return_value.__aenter__.return_value = AsyncMock()

        response = client.get("/api/audit/export?format=invalid")
        assert response.status_code == 400
        assert "Unsupported format" in response.json()["detail"]

    @patch("app.routers.audit.get_db")
    async def test_get_retention_info(self, mock_get_db: AsyncMock) -> None:
        """Test getting retention info."""
        mock_db = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db

        mock_retention_service = AsyncMock()
        mock_retention_service.get_expired_events_cutoff.return_value = datetime.now(
            UTC
        ) - timedelta(days=365)
        mock_retention_service.count_expired_events.return_value = 10

        with patch(
            "app.services.audit_retention.AuditRetentionService",
            return_value=mock_retention_service,
        ):
            response = client.get("/api/audit/retention/info")
            assert response.status_code == 200
            data = response.json()
            assert data["retention_days"] == settings.audit_retention_days
            assert data["expired_events_count"] == 10
            assert "cutoff_date" in data
