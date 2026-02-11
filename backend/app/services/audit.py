"""Audit logging service for security events."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from app.database.models import AuditEvent
from app.utils.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


class AuditService:
    """Service for logging audit events."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize audit service with database session."""
        self.db = db

    async def log_event(
        self,
        network_id: str,
        actor: str,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Log an audit event.

        Args:
            network_id: ID of the network the event relates to
            actor: Who performed the action (e.g., user ID, IP address, "system")
            action: The action performed (e.g., "CREATE", "UPDATE", "DELETE", "LOGIN")
            resource_type: Type of resource affected (e.g., "network", "device", "api_key")
            resource_id: ID of the specific resource affected
            details: Additional details about the event (will be JSON serialized)
        """
        # Convert details dict to JSON string if provided
        details_json = None
        if details:
            sanitized_details = self._sanitize_details(details)
            if sanitized_details:
                details_json = json.dumps(sanitized_details, separators=(",", ":"))

        audit_event = AuditEvent(
            id=str(uuid4()),
            network_id=network_id,
            actor=actor,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details_json,
        )

        self.db.add(audit_event)
        await self.db.commit()

        logger.info(
            "Audit event logged",
            extra={
                "event_id": audit_event.id,
                "network_id": network_id,
                "actor": actor,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "has_details": details_json is not None,
            },
        )

    def _sanitize_details(
        self, details: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        """Remove sensitive information from audit details."""
        if details is None:
            return None

        sensitive_patterns = {
            "private",
            "private_key",
            "private_key_encrypted",
            "public_key",
            "preshared_key",
            "preshared_key_encrypted",
            "network_preshared_key_encrypted",
            "password",
            "secret",
            "token",
            "key_hash",
            "key_fingerprint",
            "api_key",
            "authorization",
            "auth",
        }

        sanitized: dict[str, Any] = {}
        for key, value in details.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in sensitive_patterns):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_details(value)
            elif isinstance(value, list):
                sanitized_list: list[Any] = []
                for item in value:
                    if isinstance(item, dict):
                        sanitized_item = self._sanitize_details(item)
                        if sanitized_item is not None:
                            sanitized_list.append(sanitized_item)
                    elif isinstance(item, str) and any(
                        sensitive in item.lower() for sensitive in sensitive_patterns
                    ):
                        sanitized_list.append("[REDACTED]")
                    else:
                        sanitized_list.append(item)
                sanitized[key] = sanitized_list
            else:
                sanitized[key] = value

        return sanitized

    async def log_api_access(
        self,
        network_id: str,
        device_id: str,
        source_ip: str,
        action: str = "CONFIG_RETRIEVAL",
        success: bool = True,
    ) -> None:
        """Log API access for device config retrieval.

        Args:
            network_id: ID of the network
            device_id: ID of the device making the request
            source_ip: Source IP address of the request
            action: The action being performed
            success: Whether the access was successful
        """
        details = {
            "source_ip": source_ip,
            "success": success,
        }

        await self.log_event(
            network_id=network_id,
            actor=f"device:{device_id}",
            action=action,
            resource_type="api_key",
            resource_id=device_id,
            details=details,
        )

    async def log_admin_action(
        self,
        network_id: str,
        admin_actor: str,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        resource_name: str | None = None,
        changes: dict[str, Any] | None = None,
    ) -> None:
        """Log administrative actions."""
        details = {
            key: value
            for key, value in (("resource_name", resource_name), ("changes", changes))
            if value is not None
        }

        await self.log_event(
            network_id=network_id,
            actor=admin_actor,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details if details else None,
        )
