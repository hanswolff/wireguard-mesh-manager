"""Pydantic schemas for backup and restore operations."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class BackupCreateResponse(BaseModel):
    """Response model for backup creation."""

    model_config = {"ser_json_bytes_sort_keys": True}

    id: str
    created_at: datetime
    description: str | None = None
    exported_by: str
    encrypted: bool
    networks_count: int
    locations_count: int
    devices_count: int
    password: str | None = None  # Only returned if a new password was generated
    backup_data: dict[str, Any]


class BackupRestoreRequest(BaseModel):
    """Request model for backup restoration."""

    model_config = {"ser_json_bytes_sort_keys": True}

    backup_data: dict[str, Any]
    password: str | None = None
    overwrite_existing: bool = False


class BackupRestoreResponse(BaseModel):
    """Response model for backup restoration."""

    model_config = {"ser_json_bytes_sort_keys": True}

    success: bool
    networks_created: int = 0
    networks_updated: int = 0
    locations_created: int = 0
    devices_created: int = 0
    errors: list[str] = []


class BackupInfoResponse(BaseModel):
    """Response model for backup information."""

    model_config = {"ser_json_bytes_sort_keys": True}

    encrypted: bool
    version: str
    exported_at: datetime | None = None
    exported_by: str | None = None
    description: str | None = None
    networks_count: int | None = None
    locations_count: int | None = None
    devices_count: int | None = None
    networks: list[dict[str, Any]] = []
    error: str | None = None


class BackupRecord(BaseModel):
    """Backup record model for database storage."""

    model_config = {"ser_json_bytes_sort_keys": True}

    id: str
    description: str | None = None
    exported_by: str
    encrypted: bool
    data: dict[str, Any]
    created_at: datetime


class RestoreRecord(BaseModel):
    """Restore record model for database storage."""

    model_config = {"ser_json_bytes_sort_keys": True}

    id: str
    backup_id: str | None = None
    networks_restored: int = 0
    networks_updated: int = 0
    locations_created: int = 0
    devices_created: int = 0
    errors: list[str] = []
    restored_at: datetime
    restored_by: str
