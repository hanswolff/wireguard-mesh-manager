"""Service layer for location operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database.models import Device, Location, WireGuardNetwork
from app.exceptions import (
    BusinessRuleViolationError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from app.services.master_password import get_master_password_cache
from app.utils.key_management import (
    decrypt_device_dek_from_json,
    decrypt_preshared_key_from_json,
    encrypt_preshared_key_with_dek,
    import_wireguard_preshared_key,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.schemas.locations import LocationCreate, LocationUpdate


class LocationService:
    """Service for managing locations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_locations(self) -> list[Location]:
        """Get all locations ordered by network and name."""
        result = await self.db.execute(
            select(Location)
            .options(selectinload(Location.network), selectinload(Location.devices))
            .order_by(Location.network_id, Location.name)
        )
        return list(result.scalars().all())

    async def get_locations_by_network(self, network_id: str) -> list[Location]:
        """Get all locations for a specific network ordered by name."""
        result = await self.db.execute(
            select(Location)
            .options(selectinload(Location.network), selectinload(Location.devices))
            .where(Location.network_id == network_id)
            .order_by(Location.name)
        )
        return list(result.scalars().all())

    async def get_location(self, location_id: str) -> Location:
        """Get a location by ID."""
        result = await self.db.execute(
            select(Location)
            .options(selectinload(Location.network), selectinload(Location.devices))
            .where(Location.id == location_id)
        )
        location = result.scalar_one_or_none()
        if not location:
            raise ResourceNotFoundError("Location", location_id)
        return location

    async def create_location(
        self, location_data: LocationCreate, session_id: str | None = None
    ) -> Location:
        """Create a new location."""
        # Verify network exists
        result = await self.db.execute(
            select(WireGuardNetwork).where(
                WireGuardNetwork.id == location_data.network_id
            )
        )
        network = result.scalar_one_or_none()
        if not network:
            raise ResourceNotFoundError("Network", location_data.network_id)

        # Check name uniqueness within network
        existing = await self.db.execute(
            select(Location).where(
                Location.network_id == location_data.network_id,
                Location.name == location_data.name,
            )
        )
        if existing.scalar_one_or_none():
            raise ResourceConflictError(
                f"Location with name '{location_data.name}' already exists in this network"
            )

        preshared_key_encrypted = None
        if location_data.preshared_key is not None:
            master_password_cache = get_master_password_cache(session_id)
            master_password = master_password_cache.get_master_password()
            if not master_password:
                raise ValueError(
                    "Master password is required to set a location preshared key. Please unlock the system."
                )
            preshared_key_encrypted = import_wireguard_preshared_key(
                location_data.preshared_key, master_password
            )

        location = Location(
            **location_data.model_dump(exclude={"preshared_key"}),
            preshared_key_encrypted=preshared_key_encrypted,
        )
        self.db.add(location)
        await self.db.commit()
        await self.db.refresh(location)
        return location

    async def update_location(
        self,
        location_id: str,
        location_data: LocationUpdate,
        session_id: str | None = None,
    ) -> Location:
        """Update a location."""
        location = await self.get_location(location_id)

        # Verify new network exists if being changed
        if location_data.network_id and location_data.network_id != location.network_id:
            result = await self.db.execute(
                select(WireGuardNetwork).where(
                    WireGuardNetwork.id == location_data.network_id
                )
            )
            network = result.scalar_one_or_none()
            if not network:
                raise ResourceNotFoundError("Network", location_data.network_id)

        # Check name uniqueness if being changed
        if location_data.name and location_data.name != location.name:
            network_id = location_data.network_id or location.network_id
            existing = await self.db.execute(
                select(Location).where(
                    Location.network_id == network_id,
                    Location.name == location_data.name,
                    Location.id != location_id,
                )
            )
            if existing.scalar_one_or_none():
                raise ResourceConflictError(
                    f"Location with name '{location_data.name}' already exists in this network"
                )

        # Update fields
        update_data = location_data.model_dump(exclude_unset=True)
        if "preshared_key" in update_data:
            master_password_cache = get_master_password_cache(session_id)
            master_password = master_password_cache.get_master_password()
            if not master_password:
                raise ValueError(
                    "Master password is required to update the location preshared key. Please unlock the system."
                )
            location.preshared_key_encrypted = import_wireguard_preshared_key(
                update_data.pop("preshared_key"), master_password
            )
            await self._refresh_location_preshared_keys(location, master_password)
        for field, value in update_data.items():
            setattr(location, field, value)

        await self.db.commit()
        await self.db.refresh(location)
        return location

    async def _refresh_location_preshared_keys(
        self, location: Location, master_password: str
    ) -> None:
        """Refresh cached location preshared keys on devices."""
        result = await self.db.execute(
            select(Device).where(Device.location_id == location.id)
        )
        devices = list(result.scalars().all())
        if not devices:
            return

        if not location.preshared_key_encrypted:
            for device in devices:
                device.location_preshared_key_encrypted = None
            return

        location_preshared_key = decrypt_preshared_key_from_json(
            location.preshared_key_encrypted, master_password
        )
        for device in devices:
            if not device.device_dek_encrypted_master:
                device.location_preshared_key_encrypted = None
                continue
            device_dek = decrypt_device_dek_from_json(
                device.device_dek_encrypted_master, master_password
            )
            device.location_preshared_key_encrypted = encrypt_preshared_key_with_dek(
                location_preshared_key, device_dek
            )

    async def delete_location(self, location_id: str) -> None:
        """Delete a location."""
        location = await self.get_location(location_id)

        # Check for associated devices
        device_result = await self.db.execute(
            select(Device).where(Device.location_id == location_id)
        )
        if device_result.scalars().first():
            raise BusinessRuleViolationError(
                "location_with_devices",
                "Cannot delete location that has devices. Move or delete all devices first.",
            )

        # Check if it's the last location in the network
        remaining_locations = await self.db.execute(
            select(Location).where(Location.network_id == location.network_id)
        )
        if len(list(remaining_locations.scalars())) <= 1:
            raise BusinessRuleViolationError(
                "last_location_in_network",
                "Cannot delete the last location in a network. Each network must have at least one location.",
            )

        await self.db.delete(location)
        await self.db.commit()
