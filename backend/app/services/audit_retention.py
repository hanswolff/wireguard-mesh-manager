"""Service for audit event retention and export operations."""

from __future__ import annotations

import csv
import inspect
import io
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import delete, func, select
from sqlalchemy.orm import joinedload

from app.config import settings
from app.database.models import AuditEvent
from app.utils.logging import get_logger

if TYPE_CHECKING:
    from typing import Any

    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


class AuditExportFormat:
    """Constants for audit export formats."""

    JSON = "json"
    CSV = "csv"


class AuditRetentionService:
    """Service for managing audit event retention and cleanup."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize retention service with database session."""
        self.db = db

    async def get_expired_events_cutoff(self) -> datetime:
        """Get the cutoff date for expired audit events."""
        cutoff_date = datetime.now(UTC) - timedelta(days=settings.audit_retention_days)
        return cutoff_date

    async def count_expired_events(self) -> int:
        """Count the number of expired audit events."""
        cutoff_date = await self.get_expired_events_cutoff()

        stmt = select(func.count(AuditEvent.id)).where(
            AuditEvent.created_at < cutoff_date
        )
        result = await self.db.execute(stmt)
        count = result.scalar()
        if inspect.isawaitable(count):
            count = await count
        return count or 0

    async def cleanup_expired_events(self) -> dict[str, Any]:
        """Remove expired audit events from the database.

        Returns:
            Dictionary with cleanup statistics including:
            - events_deleted: Number of events deleted
            - cutoff_date: The cutoff date used for deletion
            - retention_days: The retention period in days
        """
        cutoff_date = await self.get_expired_events_cutoff()
        events_count = await self.count_expired_events()

        if events_count == 0:
            logger.info("No expired audit events to clean up")
            return {
                "events_deleted": 0,
                "cutoff_date": cutoff_date.isoformat(),
                "retention_days": settings.audit_retention_days,
            }

        delete_stmt = delete(AuditEvent).where(AuditEvent.created_at < cutoff_date)
        await self.db.execute(delete_stmt)
        await self.db.commit()

        logger.info(
            "Cleaned up expired audit events",
            extra={
                "events_deleted": events_count,
                "cutoff_date": cutoff_date.isoformat(),
                "retention_days": settings.audit_retention_days,
            },
        )

        return {
            "events_deleted": events_count,
            "cutoff_date": cutoff_date.isoformat(),
            "retention_days": settings.audit_retention_days,
        }


def _calculate_storage_size() -> dict[str, Any]:
    """Calculate storage size of database and related files.

    Returns:
        Dictionary containing:
        - total_size_bytes: Total size in bytes
        - database_size_bytes: Size of main database file
        - wal_size_bytes: Size of WAL files (if any)
        - shm_size_bytes: Size of SHM files (if any)
        - backup_size_bytes: Size of backup files (if any)
        - breakdown: Detailed breakdown by file
    """
    # Get database path from settings
    db_path_str = settings.database_url.replace("sqlite+aiosqlite:///", "")
    db_path = Path(db_path_str)

    if not db_path.is_absolute():
        db_path = Path.cwd() / db_path

    # Initialize counters
    database_size = 0
    wal_size = 0
    shm_size = 0
    backup_size = 0
    breakdown: list[dict[str, str | int]] = []

    # Main database file
    if db_path.exists():
        database_size = db_path.stat().st_size
        breakdown.append({
            "file": db_path.name,
            "path": str(db_path),
            "size_bytes": database_size,
            "type": "database",
        })

    # WAL file (Write-Ahead Log)
    wal_path = db_path.with_suffix(db_path.suffix + "-wal")
    if wal_path.exists():
        wal_size = wal_path.stat().st_size
        breakdown.append({
            "file": wal_path.name,
            "path": str(wal_path),
            "size_bytes": wal_size,
            "type": "wal",
        })

    # SHM file (Shared Memory)
    shm_path = db_path.with_suffix(db_path.suffix + "-shm")
    if shm_path.exists():
        shm_size = shm_path.stat().st_size
        breakdown.append({
            "file": shm_path.name,
            "path": str(shm_path),
            "size_bytes": shm_size,
            "type": "shm",
        })

    # Journal file (older SQLite versions)
    journal_path = db_path.with_suffix(db_path.suffix + "-journal")
    if journal_path.exists():
        backup_size += journal_path.stat().st_size
        breakdown.append({
            "file": journal_path.name,
            "path": str(journal_path),
            "size_bytes": journal_path.stat().st_size,
            "type": "journal",
        })

    # Backup files (*.bak, *.backup)
    backup_patterns = ["*.bak", "*.backup"]
    for pattern in backup_patterns:
        for backup_file in db_path.parent.glob(pattern):
            backup_size += backup_file.stat().st_size
            breakdown.append({
                "file": backup_file.name,
                "path": str(backup_file),
                "size_bytes": backup_file.stat().st_size,
                "type": "backup",
            })

    total_size = database_size + wal_size + shm_size + backup_size

    return {
        "total_size_bytes": total_size,
        "database_size_bytes": database_size,
        "wal_size_bytes": wal_size,
        "shm_size_bytes": shm_size,
        "backup_size_bytes": backup_size,
        "breakdown": breakdown,
    }


class AuditExportService:
    """Service for exporting audit events."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize export service with database session."""
        self.db = db

    async def export_audit_events(
        self,
        network_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        actor_filter: str | None = None,
        action_filter: str | None = None,
        format_type: str = AuditExportFormat.JSON,
        include_details: bool = True,
    ) -> dict[str, Any]:
        """Export audit events with optional filtering.

        Args:
            network_id: Optional network ID to filter events
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            actor_filter: Optional actor name filter
            action_filter: Optional action type filter
            format_type: Export format ('json' or 'csv')
            include_details: Whether to include event details

        Returns:
            Dictionary containing exported data and metadata
        """
        # Build base query
        stmt = (
            select(AuditEvent)
            .options(joinedload(AuditEvent.network))
            .order_by(AuditEvent.created_at.desc())
        )

        # Apply filters
        if network_id:
            stmt = stmt.where(AuditEvent.network_id == network_id)

        if start_date:
            stmt = stmt.where(AuditEvent.created_at >= start_date)

        if end_date:
            stmt = stmt.where(AuditEvent.created_at <= end_date)

        if actor_filter:
            stmt = stmt.where(AuditEvent.actor.ilike(f"%{actor_filter}%"))

        if action_filter:
            stmt = stmt.where(AuditEvent.action == action_filter)

        # Execute query with batching
        events: list[AuditEvent] = []
        offset = 0

        while True:
            batch_stmt = stmt.offset(offset).limit(settings.audit_export_batch_size)
            result = await self.db.execute(batch_stmt)
            batch_events = result.scalars().unique().all()

            if not batch_events:
                break

            events.extend(batch_events)
            offset += settings.audit_export_batch_size

        # Convert to requested format
        export_data: list[dict[str, Any]] | str
        if format_type == AuditExportFormat.JSON:
            export_data = self._convert_to_json(events, include_details)
        elif format_type == AuditExportFormat.CSV:
            export_data = self._convert_to_csv(
                events, include_details
            )  # CSV returns string, JSON returns list
        else:
            raise ValueError(f"Unsupported export format: {format_type}")

        logger.info(
            "Exported audit events",
            extra={
                "event_count": len(events),
                "format": format_type,
                "network_id": network_id,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
            },
        )

        return {
            "events": export_data,
            "metadata": {
                "total_events": len(events),
                "export_format": format_type,
                "exported_at": datetime.now(UTC).isoformat(),
                "filters": {
                    "network_id": network_id,
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                    "actor": actor_filter,
                    "action": action_filter,
                },
                "include_details": include_details,
            },
        }

    def _convert_to_json(
        self, events: list[AuditEvent], include_details: bool
    ) -> list[dict[str, Any]]:
        """Convert audit events to JSON format."""
        return [
            {
                "id": str(event.id),
                "network_id": str(event.network_id),
                "network_name": event.network.name if event.network else None,
                "actor": event.actor,
                "action": event.action,
                "resource_type": event.resource_type,
                "resource_id": event.resource_id,
                "created_at": event.created_at.isoformat(),
                "details": (
                    json.loads(event.details)
                    if (include_details and event.details)
                    else None
                ),
            }
            for event in events
        ]

    def _convert_to_csv(self, events: list[AuditEvent], include_details: bool) -> str:
        """Convert audit events to CSV format."""
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        headers = [
            "id",
            "network_id",
            "network_name",
            "actor",
            "action",
            "resource_type",
            "resource_id",
            "created_at",
        ]
        if include_details:
            headers.append("details")
        writer.writerow(headers)

        # Write events
        for event in events:
            row = [
                str(event.id),
                str(event.network_id),
                event.network.name if event.network else "",
                event.actor,
                event.action,
                event.resource_type,
                event.resource_id or "",
                event.created_at.isoformat(),
            ]
            if include_details:
                row.append(event.details or "")
            writer.writerow(row)

        return output.getvalue()

    async def get_audit_statistics(self) -> dict[str, Any]:
        """Get statistics about audit events."""
        # Total events count
        total_stmt = select(func.count(AuditEvent.id))
        total_result = await self.db.execute(total_stmt)
        total_events = total_result.scalar()
        if inspect.isawaitable(total_events):
            total_events = await total_events
        total_events = total_events or 0

        # Recent events (last 24 hours)
        recent_cutoff_24h = datetime.now(UTC) - timedelta(days=1)
        recent_24h_stmt = select(func.count(AuditEvent.id)).where(
            AuditEvent.created_at >= recent_cutoff_24h
        )
        recent_24h_result = await self.db.execute(recent_24h_stmt)
        recent_events_24h = recent_24h_result.scalar()
        if inspect.isawaitable(recent_events_24h):
            recent_events_24h = await recent_events_24h
        recent_events_24h = recent_events_24h or 0

        # Recent events (last 7 days)
        recent_cutoff_7d = datetime.now(UTC) - timedelta(days=7)
        recent_7d_stmt = select(func.count(AuditEvent.id)).where(
            AuditEvent.created_at >= recent_cutoff_7d
        )
        recent_7d_result = await self.db.execute(recent_7d_stmt)
        recent_events_7d = recent_7d_result.scalar()
        if inspect.isawaitable(recent_events_7d):
            recent_events_7d = await recent_events_7d
        recent_events_7d = recent_events_7d or 0

        # Events by action type (for breakdown)
        action_stmt = (
            select(AuditEvent.action, func.count(AuditEvent.id))
            .group_by(AuditEvent.action)
            .order_by(func.count(AuditEvent.id).desc())
        )
        action_result = await self.db.execute(action_stmt)
        actions_breakdown = [
            {"action": action, "count": count}
            for action, count in action_result.fetchall()
        ]

        # Recent events by action type (last 24 hours)
        recent_action_stmt = (
            select(AuditEvent.action, func.count(AuditEvent.id))
            .where(AuditEvent.created_at >= recent_cutoff_24h)
            .group_by(AuditEvent.action)
            .order_by(func.count(AuditEvent.id).desc())
        )
        recent_action_result = await self.db.execute(recent_action_stmt)
        recent_actions_breakdown = [
            {"action": action, "count": count}
            for action, count in recent_action_result.fetchall()
        ]

        # Recent events by action type (last 7 days)
        recent_7d_action_stmt = (
            select(AuditEvent.action, func.count(AuditEvent.id))
            .where(AuditEvent.created_at >= recent_cutoff_7d)
            .group_by(AuditEvent.action)
            .order_by(func.count(AuditEvent.id).desc())
        )
        recent_7d_action_result = await self.db.execute(recent_7d_action_stmt)
        recent_7d_actions_breakdown = [
            {"action": action, "count": count}
            for action, count in recent_7d_action_result.fetchall()
        ]

        # Expired events count
        retention_service = AuditRetentionService(self.db)
        expired_events = await retention_service.count_expired_events()

        # Calculate storage size
        storage_size = _calculate_storage_size()

        return {
            "total_events": total_events,
            "recent_events_24h": recent_events_24h,
            "recent_events_7d": recent_events_7d,
            "expired_events": expired_events,
            "actions_breakdown": actions_breakdown,
            "recent_actions_breakdown_24h": recent_actions_breakdown,
            "recent_actions_breakdown_7d": recent_7d_actions_breakdown,
            "retention_days": settings.audit_retention_days,
            "storage_stats": {
                "total_size_bytes": storage_size["total_size_bytes"],
                "database_size_bytes": storage_size["database_size_bytes"],
                "wal_size_bytes": storage_size["wal_size_bytes"],
                "shm_size_bytes": storage_size["shm_size_bytes"],
                "backup_size_bytes": storage_size["backup_size_bytes"],
                "breakdown": storage_size["breakdown"],
                "events_per_day": round(
                    total_events / max(1, settings.audit_retention_days), 2
                ),
            },
        }
