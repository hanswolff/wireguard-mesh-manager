"""Service for handling master password rotation and key re-encryption.

For mesh topology, networks do not have their own WireGuard keys.
Only device DEKs and preshared keys are rotated during master password changes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from app.database.models import Device, DevicePeerLink
from app.schemas.key_rotation import KeyRotationStatus
from app.utils.key_management import (
    decrypt_device_dek_from_json,
    decrypt_preshared_key_from_json,
    decrypt_private_key_from_json,
    encrypt_device_dek_with_master,
    encrypt_preshared_key,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

KEYS_PER_DEVICE = 2


class KeyRotationService:
    """Service for rotating master password and re-encrypting device DEKs.

    For mesh topology, only device DEKs and preshared keys are rotated.
    Networks do not have their own WireGuard keys.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def validate_current_password(self, current_password: str) -> bool:
        """Validate the current master password by attempting to decrypt keys.

        Args:
            current_password: Current master password to validate

        Returns:
            True if password is valid, False otherwise
        """
        device = await self._get_first_device()
        if device:
            if device.device_dek_encrypted_master:
                return self._try_decrypt_key(
                    device.device_dek_encrypted_master,
                    current_password,
                    is_device_dek=True,
                )
            return self._try_decrypt_key(device.private_key_encrypted, current_password)

        return True

    async def _get_first_device(self) -> Device | None:
        """Get first device."""
        stmt = select(Device).limit(1)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    def _try_decrypt_key(
        self, encrypted_key: str, password: str, *, is_device_dek: bool = False
    ) -> bool:
        """Try to decrypt a key with the given password."""
        try:
            if is_device_dek:
                decrypt_device_dek_from_json(encrypted_key, password)
            else:
                decrypt_private_key_from_json(encrypted_key, password)
            return True
        except (ValueError, KeyError, TypeError):
            return False

    async def rotate_master_password(
        self, current_password: str, new_password: str
    ) -> KeyRotationStatus:
        """Rotate master password and re-encrypt all device keys.

        Args:
            current_password: Current master password
            new_password: New master password

        Returns:
            KeyRotationStatus with rotation results
        """
        if not await self.validate_current_password(current_password):
            raise ValueError("Invalid current master password")

        devices = await self._get_all_devices()

        status = KeyRotationStatus(
            total_networks=0,
            total_devices=len(devices),
            rotated_networks=0,
            rotated_devices=0,
            failed_networks=0,
            failed_devices=0,
            errors=[],
        )

        await self._rotate_device_keys_batch(
            devices, current_password, new_password, status
        )
        await self._rotate_peer_link_keys(current_password, new_password)

        if status.rotated_devices > 0:
            await self.db.commit()
        else:
            await self.db.rollback()

        return status

    async def _get_all_devices(self) -> list[Device]:
        """Get all devices."""
        stmt = select(Device)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _get_all_peer_links(self) -> list[DevicePeerLink]:
        """Get all device peer links."""
        stmt = select(DevicePeerLink)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _rotate_device_keys_batch(
        self,
        devices: list[Device],
        current_password: str,
        new_password: str,
        status: KeyRotationStatus,
    ) -> None:
        """Rotate keys for a batch of devices."""
        for device in devices:
            try:
                await self._rotate_device_keys(device, current_password, new_password)
                status.rotated_devices += 1
            except (ValueError, KeyError, TypeError) as e:
                status.failed_devices += 1
                status.errors.append(f"Device '{device.name}': {str(e)}")

    async def _rotate_device_keys(
        self, device: Device, current_password: str, new_password: str
    ) -> None:
        """Rotate keys for a single device."""
        if not device.device_dek_encrypted_master:
            raise ValueError("Device is missing a master-encrypted DEK")

        device_dek = decrypt_device_dek_from_json(
            device.device_dek_encrypted_master, current_password
        )
        device.device_dek_encrypted_master = encrypt_device_dek_with_master(
            device_dek, new_password
        )

        if device.preshared_key_encrypted:
            preshared_key = decrypt_preshared_key_from_json(
                device.preshared_key_encrypted, current_password
            )
            if preshared_key:
                encrypted_psk = encrypt_preshared_key(preshared_key, new_password)
                assert encrypted_psk is not None
                device.preshared_key_encrypted = encrypted_psk

    async def _rotate_peer_link_keys(
        self, current_password: str, new_password: str
    ) -> None:
        """Rotate preshared keys stored on peer links."""
        links = await self._get_all_peer_links()
        for link in links:
            if not link.preshared_key_encrypted:
                continue
            preshared_key = decrypt_preshared_key_from_json(
                link.preshared_key_encrypted, current_password
            )
            if preshared_key:
                encrypted_psk = encrypt_preshared_key(preshared_key, new_password)
                assert encrypted_psk is not None
                link.preshared_key_encrypted = encrypted_psk

    async def get_rotation_estimate(self) -> dict[str, Any]:
        """Get estimate of items to be rotated."""
        devices = await self._get_all_devices()

        return {
            "total_networks": 0,
            "total_devices": len(devices),
            "total_keys": len(devices) * KEYS_PER_DEVICE,
        }
