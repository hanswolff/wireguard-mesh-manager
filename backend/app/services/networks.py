"""Service layer for WireGuard network operations."""

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

    from app.schemas.networks import WireGuardNetworkCreate, WireGuardNetworkUpdate


class NetworkService:
    """Service for managing WireGuard networks."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_networks(self) -> list[WireGuardNetwork]:
        """Get all networks with their counts."""
        result = await self.db.execute(
            select(WireGuardNetwork)
            .where(WireGuardNetwork.name != "__system_reference__")
            .options(
                selectinload(WireGuardNetwork.locations),
                selectinload(WireGuardNetwork.devices),
            )
        )
        return list(result.scalars().all())

    async def get_network(self, network_id: str) -> WireGuardNetwork:
        """Get a network by ID."""
        result = await self.db.execute(
            select(WireGuardNetwork)
            .options(
                selectinload(WireGuardNetwork.locations),
                selectinload(WireGuardNetwork.devices),
            )
            .where(WireGuardNetwork.id == network_id)
        )
        network = result.scalar_one_or_none()
        if not network:
            raise ResourceNotFoundError("Network", network_id)
        return network

    async def create_network(
        self, network_data: WireGuardNetworkCreate, session_id: str | None = None
    ) -> WireGuardNetwork:
        """Create a new network.

        For mesh topology, networks do not have their own WireGuard keys.
        Only devices have keys, and they communicate directly with each other.
        """
        # Check for name uniqueness
        existing = await self.db.execute(
            select(WireGuardNetwork).where(WireGuardNetwork.name == network_data.name)
        )
        if existing.scalar_one_or_none():
            raise ResourceConflictError(
                f"Network with name '{network_data.name}' already exists"
            )

        # Check for network_cidr uniqueness
        existing_cidr = await self.db.execute(
            select(WireGuardNetwork).where(
                WireGuardNetwork.network_cidr == network_data.network_cidr
            )
        )
        if existing_cidr.scalar_one_or_none():
            raise ResourceConflictError(
                f"Network with CIDR '{network_data.network_cidr}' already exists"
            )

        preshared_key_encrypted = None
        if network_data.preshared_key is not None:
            master_password_cache = get_master_password_cache(session_id)
            master_password = master_password_cache.get_master_password()
            if not master_password:
                raise ValueError(
                    "Master password is required to set a network preshared key. Please unlock the system."
                )
            preshared_key_encrypted = import_wireguard_preshared_key(
                network_data.preshared_key, master_password
            )

        # For mesh topology, networks don't have their own keys
        network = WireGuardNetwork(
            **network_data.model_dump(exclude={"preshared_key"}),
            preshared_key_encrypted=preshared_key_encrypted,
        )
        self.db.add(network)
        await self.db.commit()
        await self.db.refresh(network)
        return network

    async def update_network(
        self,
        network_id: str,
        network_data: WireGuardNetworkUpdate,
        session_id: str | None = None,
    ) -> WireGuardNetwork:
        """Update a network."""
        network = await self.get_network(network_id)

        # Check name uniqueness if being updated
        if network_data.name and network_data.name != network.name:
            existing = await self.db.execute(
                select(WireGuardNetwork).where(
                    WireGuardNetwork.name == network_data.name
                )
            )
            if existing.scalar_one_or_none():
                raise ResourceConflictError(
                    f"Network with name '{network_data.name}' already exists"
                )

        # Check network_cidr uniqueness if being updated
        if network_data.network_cidr and network_data.network_cidr != network.network_cidr:
            existing_cidr = await self.db.execute(
                select(WireGuardNetwork).where(
                    WireGuardNetwork.network_cidr == network_data.network_cidr
                )
            )
            if existing_cidr.scalar_one_or_none():
                raise ResourceConflictError(
                    f"Network with CIDR '{network_data.network_cidr}' already exists"
                )

        # Update fields
        update_data = network_data.model_dump(exclude_unset=True)
        if "preshared_key" in update_data:
            master_password_cache = get_master_password_cache(session_id)
            master_password = master_password_cache.get_master_password()
            if not master_password:
                raise ValueError(
                    "Master password is required to update the network preshared key. Please unlock the system."
                )
            network.preshared_key_encrypted = import_wireguard_preshared_key(
                update_data.pop("preshared_key"), master_password
            )
            await self._refresh_network_preshared_keys(network, master_password)
        for field, value in update_data.items():
            setattr(network, field, value)

        await self.db.commit()

        # Refresh with relationships loaded
        await self.db.refresh(network)
        result = await self.db.execute(
            select(WireGuardNetwork)
            .options(
                selectinload(WireGuardNetwork.locations),
                selectinload(WireGuardNetwork.devices),
            )
            .where(WireGuardNetwork.id == network.id)
        )
        return result.scalar_one()

    async def _refresh_network_preshared_keys(
        self, network: WireGuardNetwork, master_password: str
    ) -> None:
        """Refresh cached network preshared keys on devices."""
        result = await self.db.execute(
            select(Device).where(Device.network_id == network.id)
        )
        devices = list(result.scalars().all())
        if not devices:
            return

        if not network.preshared_key_encrypted:
            for device in devices:
                device.network_preshared_key_encrypted = None
            return

        network_preshared_key = decrypt_preshared_key_from_json(
            network.preshared_key_encrypted, master_password
        )
        for device in devices:
            if not device.device_dek_encrypted_master:
                device.network_preshared_key_encrypted = None
                continue
            device_dek = decrypt_device_dek_from_json(
                device.device_dek_encrypted_master, master_password
            )
            device.network_preshared_key_encrypted = encrypt_preshared_key_with_dek(
                network_preshared_key, device_dek
            )

    async def delete_network(self, network_id: str) -> None:
        """Delete a network."""
        # Check for associated locations first
        from sqlalchemy import func

        location_count_result = await self.db.execute(
            select(func.count(Location.id)).where(Location.network_id == network_id)
        )
        location_count = location_count_result.scalar() or 0

        if location_count > 0:
            raise BusinessRuleViolationError(
                "network_with_locations",
                "Cannot delete network that has locations. Delete all locations first.",
            )

        # Now get the network for deletion
        network = await self.get_network(network_id)
        await self.db.delete(network)
        await self.db.commit()
