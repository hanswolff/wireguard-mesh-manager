"""Service for device-to-device peer properties."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.database.models import Device, DevicePeerLink
from app.services.master_password import get_master_password_cache
from app.utils.key_management import (
    decrypt_device_dek_from_json,
    encrypt_preshared_key_with_dek,
    import_wireguard_preshared_key,
)


class DevicePeerLinkService:
    """Service for managing directional device peer link properties."""

    def __init__(self, db: Any) -> None:
        self.db = db

    async def list_links(self, network_id: str) -> list[DevicePeerLink]:
        """List all peer links for a network."""
        result = await self.db.execute(
            select(DevicePeerLink).where(DevicePeerLink.network_id == network_id)
        )
        return list(result.scalars().all())

    async def upsert_link(
        self,
        network_id: str,
        *,
        from_device_id: str,
        to_device_id: str,
        properties: dict[str, Any] | None,
        preshared_key: str | None,
        preshared_key_set: bool,
        session_id: str | None = None,
    ) -> DevicePeerLink | None:
        """Create or update a directional device peer link."""
        if from_device_id == to_device_id:
            raise ValueError("Device links must be directional and cannot be self-referential")

        devices = await self._load_devices(from_device_id, to_device_id)
        if len(devices) != 2:
            raise ValueError("Both devices must exist to configure a link")

        from_device, to_device = devices
        if from_device.network_id != network_id or to_device.network_id != network_id:
            raise ValueError("Devices must belong to the specified network")

        normalized = self._normalize_properties(properties)
        result = await self.db.execute(
            select(DevicePeerLink).where(
                DevicePeerLink.network_id == network_id,
                DevicePeerLink.from_device_id == from_device_id,
                DevicePeerLink.to_device_id == to_device_id,
            )
        )
        existing = result.scalar_one_or_none()

        if not normalized and not preshared_key_set:
            raise ValueError(
                "At least one peer property or preshared key is required for a link"
            )
        if (
            not existing
            and not normalized
            and preshared_key_set
            and preshared_key is None
        ):
            raise ValueError(
                "At least one peer property or preshared key is required for a link"
            )

        preshared_key_encrypted = None
        preshared_key_encrypted_dek = None
        if preshared_key_set:
            if preshared_key is None:
                preshared_key_encrypted = None
                preshared_key_encrypted_dek = None
            else:
                master_password_cache = get_master_password_cache(session_id)
                master_password = master_password_cache.get_master_password()
                if not master_password:
                    raise ValueError(
                        "Master password is required to set per-peer preshared keys. Please unlock the system."
                    )
                if not from_device.device_dek_encrypted_master:
                    raise ValueError(
                        "Device is missing a master-encrypted DEK for preshared key setup."
                    )
                device_dek = decrypt_device_dek_from_json(
                    from_device.device_dek_encrypted_master, master_password
                )
                preshared_key_encrypted = import_wireguard_preshared_key(
                    preshared_key, master_password
                )
                preshared_key_encrypted_dek = encrypt_preshared_key_with_dek(
                    preshared_key, device_dek
                )

        if existing:
            if normalized is not None:
                existing.properties = normalized
            if preshared_key_set:
                existing.preshared_key_encrypted = preshared_key_encrypted
                existing.preshared_key_encrypted_dek = preshared_key_encrypted_dek
            await self.db.commit()
            await self.db.refresh(existing)
            return existing

        link = DevicePeerLink(
            network_id=network_id,
            from_device_id=from_device_id,
            to_device_id=to_device_id,
            properties=normalized,
            preshared_key_encrypted=preshared_key_encrypted,
            preshared_key_encrypted_dek=preshared_key_encrypted_dek,
        )
        self.db.add(link)
        await self.db.commit()
        await self.db.refresh(link)
        return link

    async def delete_link(
        self, network_id: str, from_device_id: str, to_device_id: str
    ) -> bool:
        """Delete a peer link if it exists."""
        result = await self.db.execute(
            select(DevicePeerLink).where(
                DevicePeerLink.network_id == network_id,
                DevicePeerLink.from_device_id == from_device_id,
                DevicePeerLink.to_device_id == to_device_id,
            )
        )
        existing = result.scalar_one_or_none()

        if not existing:
            return False
        await self.db.delete(existing)
        await self.db.commit()
        return True

    async def _load_devices(self, from_device_id: str, to_device_id: str) -> list[Device]:
        result = await self.db.execute(
            select(Device).where(Device.id.in_([from_device_id, to_device_id]))
        )
        devices = list(result.scalars().all())
        devices.sort(key=lambda device: device.id != from_device_id)
        return devices

    def _normalize_properties(
        self, properties: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        if not properties:
            return None

        normalized: dict[str, Any] = {}
        for key, value in properties.items():
            if key == "PersistentKeepalive":
                normalized[key] = None if value is None else int(value)
                continue
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            normalized[key] = value

        return normalized or None
