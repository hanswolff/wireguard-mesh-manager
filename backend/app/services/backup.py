"""Service for backup operations."""

from __future__ import annotations

import secrets
import string
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from app.database.models import AuditEvent
from app.services.export import ExportImportService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.schemas.export import ExportData


class BackupRecord:
    """Simple backup record for audit purposes."""

    def __init__(
        self,
        audit_event: AuditEvent,
        description: str | None,
        exported_by: str,
        encrypted: bool,
    ) -> None:
        self.id = str(audit_event.id)
        self.description = description
        self.exported_by = exported_by
        self.encrypted = encrypted
        self.created_at = audit_event.occurred_at


class BackupService:
    """Service for managing backup operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.export_service = ExportImportService(db)

    async def export_networks(
        self, exported_by: str, description: str | None = None
    ) -> ExportData:
        """Export all networks using the existing export service."""
        return await self.export_service.export_networks(
            exported_by,
            description,
            network_ids=None,
            include_encrypted_keys=True,
        )

    def generate_password(self, length: int = 32) -> str:
        """Generate a secure random password for backup encryption."""
        if length < 4:
            raise ValueError("Password length must be at least 4 characters")

        specials = "!@#$%^&*"
        required_chars = [
            secrets.choice(string.ascii_lowercase),
            secrets.choice(string.ascii_uppercase),
            secrets.choice(string.digits),
            secrets.choice(specials),
        ]

        alphabet = string.ascii_letters + string.digits + specials
        remaining = length - len(required_chars)
        password_chars = required_chars + [
            secrets.choice(alphabet) for _ in range(remaining)
        ]
        secrets.SystemRandom().shuffle(password_chars)
        return "".join(password_chars)

    async def create_backup_record(
        self,
        description: str | None,
        exported_by: str,
        encrypted: bool,
        data: dict[str, Any],
    ) -> BackupRecord:
        """Create a backup audit record.

        Note: In a full implementation, this would store in a backups table.
        For now, we create an audit event.
        """
        # Count items in the backup
        networks_count: str | int
        locations_count: str | int
        devices_count: str | int
        if data.get("encrypted"):
            networks_count = "unknown"
            locations_count = "unknown"
            devices_count = "unknown"
        else:
            networks_count = len(data.get("networks", []))
            locations_count = sum(
                len(network.get("locations", []))
                for network in data.get("networks", [])
            )
            devices_count = sum(
                len(network.get("devices", [])) for network in data.get("networks", [])
            )

        # Create audit event
        audit = AuditEvent(
            action="backup_created",
            actor=exported_by,
            resource_type="backup",
            resource_id=None,
            details={
                "description": description,
                "encrypted": encrypted,
                "networks_count": networks_count,
                "locations_count": locations_count,
                "devices_count": devices_count,
            },
            occurred_at=datetime.now(UTC),
        )
        self.db.add(audit)
        await self.db.flush()

        return BackupRecord(audit, description, exported_by, encrypted)

    async def create_restore_record(
        self,
        networks_restored: int,
        networks_updated: int,
        locations_created: int,
        devices_created: int,
        errors: list[str],
        restored_by: str = "api",
    ) -> AuditEvent:
        """Create a restore audit record."""
        audit = AuditEvent(
            action="backup_restored",
            actor=restored_by,
            resource_type="backup",
            resource_id=None,
            details={
                "networks_restored": networks_restored,
                "networks_updated": networks_updated,
                "locations_created": locations_created,
                "devices_created": devices_created,
                "errors_count": len(errors),
                "errors": errors[:5],  # Store first 5 errors
            },
            occurred_at=datetime.now(UTC),
        )
        self.db.add(audit)
        await self.db.flush()
        return audit
