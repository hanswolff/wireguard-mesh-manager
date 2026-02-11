"""Service for API key lifecycle management."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.database.models import APIKey, Device
from app.utils.api_key import (
    APIKeyNotFoundError,
    DeviceNotFoundError,
    parse_expiry_timestamp,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.schemas.devices import APIKeyCreate, APIKeyUpdate


class APIKeyService:
    """Service for managing API keys."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize the service."""
        self.db = db

    async def _get_device_or_raise(self, device_id: str) -> Device:
        """Get device by ID or raise DeviceNotFoundError."""
        result = await self.db.execute(
            select(Device)
            .options(joinedload(Device.network))
            .where(Device.id == device_id)
        )
        device = result.scalar_one_or_none()
        if not device:
            raise DeviceNotFoundError(device_id)
        return device

    async def list_api_keys(self, device_id: str | None = None) -> list[APIKey]:
        """List API keys, optionally filtered by device ID."""
        query = select(APIKey).options(
            joinedload(APIKey.device), joinedload(APIKey.network)
        )

        if device_id:
            query = query.where(APIKey.device_id == device_id)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_api_key(self, api_key_id: str) -> APIKey:
        """Get a specific API key by ID."""
        result = await self.db.execute(
            select(APIKey)
            .options(joinedload(APIKey.device), joinedload(APIKey.network))
            .where(APIKey.id == api_key_id)
        )
        api_key = result.scalar_one_or_none()
        if not api_key:
            raise APIKeyNotFoundError(api_key_id)
        return api_key

    async def get_api_keys_by_device(self, device_id: str) -> list[APIKey]:
        """Get all API keys for a specific device."""
        await self._get_device_or_raise(device_id)

        result = await self.db.execute(
            select(APIKey)
            .options(joinedload(APIKey.device), joinedload(APIKey.network))
            .where(APIKey.device_id == device_id)
        )
        return list(result.scalars().all())

    async def create_api_key(
        self,
        api_key_data: APIKeyCreate,
        key_hash: str,
        key_fingerprint: str | None = None,
    ) -> APIKey:
        """Create a new API key for a device."""
        device = await self._get_device_or_raise(api_key_data.device_id)
        expires_at = parse_expiry_timestamp(api_key_data.expires_at)
        allowed_ip_ranges = (
            api_key_data.allowed_ip_ranges
            if api_key_data.allowed_ip_ranges is not None
            else ""
        )

        api_key = APIKey(
            device_id=api_key_data.device_id,
            network_id=device.network_id,
            key_hash=key_hash,
            key_fingerprint=key_fingerprint,
            name=api_key_data.name,
            allowed_ip_ranges=allowed_ip_ranges,
            enabled=api_key_data.enabled,
            expires_at=expires_at,
        )

        self.db.add(api_key)
        await self.db.commit()
        await self.db.refresh(api_key, ["device", "network"])
        return api_key

    async def update_api_key(
        self, api_key_id: str, api_key_data: APIKeyUpdate
    ) -> APIKey:
        """Update an API key."""
        api_key = await self.get_api_key(api_key_id)

        if api_key_data.name is not None:
            api_key.name = api_key_data.name

        if api_key_data.allowed_ip_ranges is not None:
            api_key.allowed_ip_ranges = api_key_data.allowed_ip_ranges

        if api_key_data.enabled is not None:
            api_key.enabled = api_key_data.enabled

        if api_key_data.expires_at is not None:
            api_key.expires_at = parse_expiry_timestamp(api_key_data.expires_at)

        await self.db.commit()
        await self.db.refresh(api_key, ["device", "network"])
        return api_key

    async def rotate_api_key(
        self, api_key_id: str, new_key_hash: str, new_key_fingerprint: str | None = None
    ) -> APIKey:
        """Rotate an API key by creating a new one and disabling the old one."""
        old_api_key = await self.get_api_key(api_key_id)

        old_api_key.enabled = False
        old_api_key.name = f"{old_api_key.name} (rotated)"
        old_api_key.device_dek_encrypted = None

        new_api_key = APIKey(
            device_id=old_api_key.device_id,
            network_id=old_api_key.network_id,
            key_hash=new_key_hash,
            key_fingerprint=new_key_fingerprint,
            name=old_api_key.name.replace(" (rotated)", ""),
            allowed_ip_ranges=old_api_key.allowed_ip_ranges,
            enabled=True,
            expires_at=old_api_key.expires_at,
        )

        self.db.add(new_api_key)
        await self.db.commit()
        await self.db.refresh(new_api_key, ["device", "network"])
        return new_api_key

    async def revoke_api_key(self, api_key_id: str) -> APIKey:
        """Revoke (disable) an API key."""
        api_key = await self.get_api_key(api_key_id)
        api_key.enabled = False
        api_key.name = f"{api_key.name} (revoked)"
        api_key.device_dek_encrypted = None
        await self.db.commit()
        return api_key

    async def delete_api_key(self, api_key_id: str) -> None:
        """Delete an API key permanently."""
        api_key = await self.get_api_key(api_key_id)
        api_key.device_dek_encrypted = None
        await self.db.delete(api_key)
        await self.db.commit()
