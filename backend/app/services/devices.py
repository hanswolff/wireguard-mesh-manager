"""Service for device management with IP allocation."""

from __future__ import annotations

import ipaddress
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database.models import APIKey, Device, DevicePeerLink, Location, WireGuardNetwork
from app.exceptions import ResourceNotFoundError
from app.services.master_password import get_master_password_cache
from app.utils.key_management import (
    decrypt_device_dek_from_json,
    decrypt_preshared_key_from_json,
    decrypt_private_key_from_json,
    derive_wireguard_public_key,
    encrypt_device_dek_with_api_key,
    encrypt_device_dek_with_master,
    encrypt_preshared_key_with_dek,
    encrypt_private_key_with_dek,
    generate_device_dek,
    generate_wireguard_private_key,
    import_wireguard_preshared_key,
    import_wireguard_private_key_with_dek,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.schemas.devices import DeviceCreate, DeviceUpdate


class DeviceService:
    """Service for managing devices with IP allocation."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _encrypt_network_preshared_key(
        self,
        network: WireGuardNetwork,
        device_dek: str,
        master_password: str,
    ) -> str | None:
        """Encrypt the network preshared key using the device DEK."""
        if not network.preshared_key_encrypted:
            return None

        preshared_key = decrypt_preshared_key_from_json(
            network.preshared_key_encrypted, master_password
        )
        return encrypt_preshared_key_with_dek(preshared_key, device_dek)

    def _encrypt_location_preshared_key(
        self,
        location: Location,
        device_dek: str,
        master_password: str,
    ) -> str | None:
        """Encrypt the location preshared key using the device DEK."""
        if not location.preshared_key_encrypted:
            return None

        preshared_key = decrypt_preshared_key_from_json(
            location.preshared_key_encrypted, master_password
        )
        return encrypt_preshared_key_with_dek(preshared_key, device_dek)

    async def list_devices(
        self,
        search: str | None = None,
        location_id: str | None = None,
        enabled: bool | None = None,
    ) -> list[Device]:
        """List all devices with optional filtering.

        Args:
            search: Filter by device name (case-insensitive partial match)
            location_id: Filter by location ID
            enabled: Filter by enabled status

        Returns:
            List of devices matching the filters
        """
        query = (
            select(Device)
            .options(
                selectinload(Device.network),
                selectinload(Device.location),
                selectinload(Device.api_keys),
            )
            .order_by(Device.created_at.desc())
        )

        # Apply filters
        if search:
            query = query.where(Device.name.ilike(f"%{search}%"))

        if location_id:
            query = query.where(Device.location_id == location_id)

        if enabled is not None:
            query = query.where(Device.enabled == enabled)

        result = await self.db.execute(query)
        return list(result.scalars().unique().all())

    async def get_device(self, device_id: str) -> Device:
        """Get a specific device by ID."""
        result = await self.db.execute(
            select(Device)
            .options(
                selectinload(Device.network),
                selectinload(Device.location),
                selectinload(Device.api_keys),
            )
            .where(Device.id == device_id)
        )
        device = result.scalar_one_or_none()
        if not device:
            raise ResourceNotFoundError("Device", device_id)
        return device

    async def get_devices_by_network(
        self,
        network_id: str,
        search: str | None = None,
        location_id: str | None = None,
        enabled: bool | None = None,
    ) -> list[Device]:
        """Get all devices in a network with optional filtering.

        Args:
            network_id: Network ID to filter devices from
            search: Filter by device name (case-insensitive partial match)
            location_id: Filter by location ID
            enabled: Filter by enabled status

        Returns:
            List of devices in the network matching the filters
        """
        query = (
            select(Device)
            .options(
                selectinload(Device.network),
                selectinload(Device.location),
                selectinload(Device.api_keys),
            )
            .where(Device.network_id == network_id)
            .order_by(Device.created_at.desc())
        )

        # Apply filters
        if search:
            query = query.where(Device.name.ilike(f"%{search}%"))

        if location_id:
            query = query.where(Device.location_id == location_id)

        if enabled is not None:
            query = query.where(Device.enabled == enabled)

        result = await self.db.execute(query)
        return list(result.scalars().unique().all())

    async def create_device(
        self, device_data: DeviceCreate, session_id: str | None = None
    ) -> Device:
        """Create a new device with IP allocation."""
        # Validate dependencies
        location = await self._validate_location_belongs_to_network(
            device_data.location_id, device_data.network_id
        )
        network = await self._get_network(device_data.network_id)

        # Validate and allocate IP
        wireguard_ip = await self._resolve_device_ip(device_data.wireguard_ip, network)

        # Get master password for key encryption
        master_password_cache = get_master_password_cache(session_id)
        master_password = master_password_cache.get_master_password()
        if not master_password:
            raise ValueError(
                "Master password is required to create devices. Please unlock the system."
            )

        # Validate endpoint uniqueness
        external_host = device_data.external_endpoint_host
        external_port = device_data.external_endpoint_port
        effective_external_host = None
        if external_port is not None:
            effective_external_host = external_host or location.external_endpoint
        await self.validate_external_endpoint_unique(
            effective_external_host, external_port, exclude_device_id=None
        )
        await self.validate_internal_endpoint_unique(
            device_data.internal_endpoint_host,
            device_data.internal_endpoint_port,
            device_data.location_id,
            exclude_device_id=None,
        )

        # Generate or import private key for the device
        private_key = device_data.private_key
        if private_key:
            public_key = derive_wireguard_public_key(private_key)
            if device_data.public_key and device_data.public_key != public_key:
                raise ValueError("Provided public key does not match private key")
        else:
            private_key = generate_wireguard_private_key()
            public_key = derive_wireguard_public_key(private_key)
        await self.validate_public_key_unique(public_key, network.id)

        device_dek = generate_device_dek()
        private_key_encrypted = import_wireguard_private_key_with_dek(
            private_key, device_dek
        )
        device_dek_encrypted_master = encrypt_device_dek_with_master(
            device_dek, master_password
        )
        network_preshared_key_encrypted = self._encrypt_network_preshared_key(
            network, device_dek, master_password
        )
        location_preshared_key_encrypted = self._encrypt_location_preshared_key(
            location, device_dek, master_password
        )

        # Encrypt preshared key if provided
        preshared_key_encrypted = import_wireguard_preshared_key(
            device_data.preshared_key, master_password
        )

        # Create device
        device = Device(
            network_id=device_data.network_id,
            location_id=device_data.location_id,
            name=device_data.name,
            description=device_data.description,
            wireguard_ip=wireguard_ip,
            external_endpoint_host=device_data.external_endpoint_host,
            external_endpoint_port=device_data.external_endpoint_port,
            internal_endpoint_host=device_data.internal_endpoint_host,
            internal_endpoint_port=device_data.internal_endpoint_port,
            public_key=public_key,
            preshared_key_encrypted=preshared_key_encrypted,
            network_preshared_key_encrypted=network_preshared_key_encrypted,
            location_preshared_key_encrypted=location_preshared_key_encrypted,
            private_key_encrypted=private_key_encrypted,
            device_dek_encrypted_master=device_dek_encrypted_master,
            enabled=device_data.enabled,
            interface_properties=device_data.interface_properties,
        )

        self.db.add(device)
        await self.db.commit()
        return await self.get_device(device.id)

    async def _resolve_device_ip(
        self, requested_ip: str | None, network: WireGuardNetwork
    ) -> str:
        """Resolve device IP - auto-allocate if not provided, validate if provided."""
        if requested_ip is None:
            return await self._allocate_next_available_ip(network)

        await self._validate_ip_in_network(requested_ip, network)
        await self._validate_ip_available(requested_ip, network.id)
        return requested_ip

    async def update_device(
        self,
        device_id: str,
        device_data: DeviceUpdate,
        session_id: str | None = None,
    ) -> Device:
        """Update an existing device."""
        device = await self.get_device(device_id)
        network = await self._get_network(device.network_id)

        update_data = device_data.model_dump(exclude_unset=True)

        # Handle field updates only when explicitly provided
        if "wireguard_ip" in update_data:
            await self._update_device_ip(
                device, update_data.get("wireguard_ip"), network
            )
        if "location_id" in update_data:
            await self._update_device_location(device, update_data.get("location_id"))
        if "public_key" in update_data:
            await self._update_device_public_key(
                device, update_data.get("public_key"), network
            )

        # Validate endpoint uniqueness before applying updates
        external_fields = {"external_endpoint_host", "external_endpoint_port"}
        internal_fields = {"internal_endpoint_host", "internal_endpoint_port"}
        location_id = update_data.get("location_id", device.location_id)

        if external_fields & update_data.keys() or "location_id" in update_data:
            external_host = update_data.get(
                "external_endpoint_host", device.external_endpoint_host
            )
            external_port = update_data.get(
                "external_endpoint_port", device.external_endpoint_port
            )
            effective_external_host = external_host
            if external_port is not None and external_host is None:
                location = await self._get_location(location_id)
                effective_external_host = location.external_endpoint
            await self.validate_external_endpoint_unique(
                effective_external_host, external_port, exclude_device_id=device.id
            )
        if internal_fields & update_data.keys():
            await self.validate_internal_endpoint_unique(
                update_data.get("internal_endpoint_host", device.internal_endpoint_host),
                update_data.get("internal_endpoint_port", device.internal_endpoint_port),
                location_id,
                exclude_device_id=device.id,
            )

        # Simple field updates
        for field in [
            "name",
            "description",
            "enabled",
            "external_endpoint_host",
            "external_endpoint_port",
            "internal_endpoint_host",
            "internal_endpoint_port",
            "interface_properties",
        ]:
            if field in update_data:
                setattr(device, field, update_data[field])

        if "private_key" in update_data:
            master_password_cache = get_master_password_cache(session_id)
            master_password = master_password_cache.get_master_password()
            if not master_password:
                raise ValueError(
                    "Master password is required to update device keys. Please unlock the system."
                )

            private_key = update_data.get("private_key")
            if private_key:
                public_key = derive_wireguard_public_key(private_key)
                if (
                    "public_key" in update_data
                    and update_data.get("public_key")
                    and update_data.get("public_key") != public_key
                ):
                    raise ValueError(
                        "Provided public key does not match private key"
                    )
                await self.validate_public_key_unique(
                    public_key, network.id, device.id
                )
                device.public_key = public_key
                device_dek = None
                if device.device_dek_encrypted_master:
                    device_dek = decrypt_device_dek_from_json(
                        device.device_dek_encrypted_master, master_password
                    )
                else:
                    device_dek = generate_device_dek()
                    device.device_dek_encrypted_master = encrypt_device_dek_with_master(
                        device_dek, master_password
                    )
                    device.device_dek_encrypted_api_key = None
                    if device.api_keys:
                        for key_obj in device.api_keys:
                            key_obj.device_dek_encrypted = None

                device.private_key_encrypted = import_wireguard_private_key_with_dek(
                    private_key, device_dek
                )
                device.network_preshared_key_encrypted = (
                    self._encrypt_network_preshared_key(
                        network, device_dek, master_password
                    )
                )
                device.location_preshared_key_encrypted = (
                    self._encrypt_location_preshared_key(
                        device.location, device_dek, master_password
                    )
                )

        if "preshared_key" in update_data:
            # Get master password for key encryption
            master_password_cache = get_master_password_cache(session_id)
            master_password = master_password_cache.get_master_password()
            if not master_password:
                raise ValueError(
                    "Master password is required to update device keys. Please unlock the system."
                )

            # Encrypt preshared key
            device.preshared_key_encrypted = import_wireguard_preshared_key(
                update_data["preshared_key"], master_password
            )  # type: ignore

        if "location_id" in update_data:
            location = await self._get_location(device.location_id)
            if location.preshared_key_encrypted:
                master_password_cache = get_master_password_cache(session_id)
                master_password = master_password_cache.get_master_password()
                if not master_password:
                    raise ValueError(
                        "Master password is required to update device location preshared keys. Please unlock the system."
                    )
                if not device.device_dek_encrypted_master:
                    raise ValueError(
                        "Device is missing a master-encrypted DEK for location preshared key updates."
                    )
                device_dek = decrypt_device_dek_from_json(
                    device.device_dek_encrypted_master, master_password
                )
                device.location_preshared_key_encrypted = (
                    self._encrypt_location_preshared_key(
                        location, device_dek, master_password
                    )
                )
            else:
                device.location_preshared_key_encrypted = None

        await self.db.commit()
        return await self.get_device(device.id)

    async def update_device_dek_for_api_key(
        self, api_key: APIKey, key_value: str, session_id: str | None = None
    ) -> None:
        """Encrypt the device DEK with a provided API key."""
        # Always fetch device explicitly to avoid lazy loading issues with api_key.device
        device = await self.get_device(api_key.device_id)
        original_device_dek_encrypted = api_key.device_dek_encrypted
        created_new_dek = False

        try:
            master_password_cache = get_master_password_cache(session_id)
            master_password = master_password_cache.get_master_password()
            if not master_password:
                raise ValueError(
                    "Master password is required to update device API key encryption."
                )

            if device.device_dek_encrypted_master:
                device_dek = decrypt_device_dek_from_json(
                    device.device_dek_encrypted_master, master_password
                )
            else:
                private_key = decrypt_private_key_from_json(
                    device.private_key_encrypted, master_password
                )
                device_dek = generate_device_dek()
                device.private_key_encrypted = encrypt_private_key_with_dek(
                    private_key, device_dek
                )
                device.device_dek_encrypted_master = encrypt_device_dek_with_master(
                    device_dek, master_password
                )
                created_new_dek = True

            if created_new_dek and device.api_keys:
                for key_obj in device.api_keys:
                    key_obj.device_dek_encrypted = None

            api_key.device_dek_encrypted = encrypt_device_dek_with_api_key(
                device_dek, key_value
            )
            device.device_dek_encrypted_api_key = None
            device.network_preshared_key_encrypted = self._encrypt_network_preshared_key(
                device.network, device_dek, master_password
            )
            device.location_preshared_key_encrypted = (
                self._encrypt_location_preshared_key(
                    device.location, device_dek, master_password
                )
            )
            await self._refresh_peer_link_preshared_keys(
                device.id, device_dek, master_password
            )
        except Exception:
            await self.db.rollback()
            await self.db.refresh(device)
            api_key.device_dek_encrypted = original_device_dek_encrypted
            raise

        await self.db.commit()

    async def _refresh_peer_link_preshared_keys(
        self, device_id: str, device_dek: str, master_password: str
    ) -> None:
        """Refresh per-peer preshared keys encrypted with the device DEK."""
        result = await self.db.execute(
            select(DevicePeerLink).where(DevicePeerLink.from_device_id == device_id)
        )
        links = list(result.scalars().all())
        if not links:
            return
        for link in links:
            if not link.preshared_key_encrypted:
                link.preshared_key_encrypted_dek = None
                continue
            preshared_key = decrypt_preshared_key_from_json(
                link.preshared_key_encrypted, master_password
            )
            link.preshared_key_encrypted_dek = encrypt_preshared_key_with_dek(
                preshared_key, device_dek
            )

    async def _update_device_ip(
        self, device: Device, new_ip: str | None, network: WireGuardNetwork
    ) -> None:
        """Update device IP if changed."""
        if new_ip == device.wireguard_ip:
            return

        if new_ip is None:
            # Clear the IP
            device.wireguard_ip = None
            return

        await self._validate_ip_in_network(new_ip, network)
        await self._validate_ip_available(new_ip, network.id, device.id)
        device.wireguard_ip = new_ip

    async def _update_device_location(
        self, device: Device, new_location_id: str | None
    ) -> None:
        """Update device location if changed."""
        if new_location_id is None or new_location_id == device.location_id:
            return

        await self._validate_location_belongs_to_network(
            new_location_id, device.network_id
        )
        device.location_id = new_location_id

    async def _update_device_public_key(
        self, device: Device, new_key: str | None, network: WireGuardNetwork
    ) -> None:
        """Update device public key if changed."""
        if new_key is None or new_key == device.public_key:
            return

        await self.validate_public_key_unique(new_key, network.id, device.id)
        device.public_key = new_key

    async def revoke_device(self, device_id: str) -> Device:
        """Revoke (disable) a device and all its API keys for emergency lockdown."""
        device = await self.get_device(device_id)

        # Disable the device
        device.enabled = False
        device.name = f"{device.name} (revoked)"

        # Disable all associated API keys
        await self._revoke_device_api_keys(device_id)

        await self.db.commit()
        return await self.get_device(device.id)

    async def _revoke_device_api_keys(self, device_id: str) -> None:
        """Disable all API keys for a device."""
        result = await self.db.execute(
            select(APIKey).where(
                APIKey.device_id == device_id, APIKey.enabled.is_(True)
            )
        )
        api_keys = list(result.scalars().all())

        for api_key in api_keys:
            api_key.enabled = False
            api_key.name = f"{api_key.name} (device revoked)"

    async def delete_device(self, device_id: str) -> Device:
        """Delete a device."""
        device = await self.get_device(device_id)
        await self.db.delete(device)
        await self.db.commit()
        return device

    async def get_available_ips(self, network_id: str) -> list[str]:
        """Get list of available IPs in a network CIDR."""
        network = await self._get_network(network_id)
        allocated_ips = await self._get_allocated_ips(network_id)

        network_ip = ipaddress.IPv4Network(network.network_cidr)
        available_ips = []

        for ip in network_ip.hosts():
            ip_str = str(ip)
            if ip_str not in allocated_ips:
                available_ips.append(ip_str)

        return available_ips

    async def _allocate_next_available_ip(self, network: WireGuardNetwork) -> str:
        """Allocate the next available IP in the network CIDR."""
        network_ip = ipaddress.IPv4Network(network.network_cidr)
        allocated_ips = await self._get_allocated_ips(network.id)

        # Iterate through host IPs (excluding network and broadcast)
        for ip in network_ip.hosts():
            ip_str = str(ip)
            if ip_str not in allocated_ips:
                return ip_str

        raise ValueError(f"No available IPs in network {network.network_cidr}")

    async def _get_allocated_ips(self, network_id: str) -> set[str]:
        """Get set of already allocated IPs in a network."""
        result = await self.db.execute(
            select(Device.wireguard_ip).where(
                Device.network_id == network_id, Device.wireguard_ip.is_not(None)
            )
        )
        return {row[0] for row in result.all()}

    async def _validate_ip_in_network(self, ip: str, network: WireGuardNetwork) -> None:
        """Validate that IP is within network CIDR."""
        try:
            ip_obj = ipaddress.IPv4Address(ip)
            network_obj = ipaddress.IPv4Network(network.network_cidr)
            if ip_obj not in network_obj:
                raise ValueError(
                    f"IP {ip} is not within network CIDR {network.network_cidr}"
                )
        except ipaddress.AddressValueError as e:
            raise ValueError(f"Invalid IP address: {ip}") from e

    async def _validate_ip_available(
        self, ip: str, network_id: str, exclude_device_id: str | None = None
    ) -> None:
        """Validate that IP is not already allocated in the network."""
        query = select(Device).where(
            Device.network_id == network_id, Device.wireguard_ip == ip
        )

        if exclude_device_id:
            query = query.where(Device.id != exclude_device_id)

        result = await self.db.execute(query)
        existing_device = result.scalar_one_or_none()

        if existing_device:
            raise ValueError(
                f"IP {ip} is already allocated to device '{existing_device.name}'"
            )

    async def _validate_public_key_unique(
        self, public_key: str, network_id: str, exclude_device_id: str | None = None
    ) -> None:
        """Validate that public key is unique within the network."""
        query = select(Device).where(
            Device.network_id == network_id, Device.public_key == public_key
        )

        if exclude_device_id:
            query = query.where(Device.id != exclude_device_id)

        result = await self.db.execute(query)
        existing_device = result.scalar_one_or_none()

        if existing_device:
            raise ValueError(
                f"Public key is already used by device '{existing_device.name}'"
            )

    async def _get_network(self, network_id: str) -> WireGuardNetwork:
        """Get network by ID."""
        result = await self.db.execute(
            select(WireGuardNetwork).where(WireGuardNetwork.id == network_id)
        )
        network = result.scalar_one_or_none()
        if not network:
            raise ResourceNotFoundError("Network", network_id)
        return network

    async def _validate_location_belongs_to_network(
        self, location_id: str, network_id: str
    ) -> Location:
        """Validate that location exists and belongs to the specified network."""
        result = await self.db.execute(
            select(Location).where(
                Location.id == location_id, Location.network_id == network_id
            )
        )
        location = result.scalar_one_or_none()
        if not location:
            raise ResourceNotFoundError("Location", location_id)
        return location

    async def _get_location(self, location_id: str) -> Location:
        """Get location by ID."""
        result = await self.db.execute(
            select(Location).where(Location.id == location_id)
        )
        location = result.scalar_one_or_none()
        if not location:
            raise ResourceNotFoundError("Location", location_id)
        return location

    async def validate_public_key_unique(
        self, public_key: str, network_id: str, exclude_device_id: str | None = None
    ) -> None:
        """Validate that public key is unique within the network.

        Args:
            public_key: The public key to validate
            network_id: ID of the network to check against
            exclude_device_id: ID of device to exclude from uniqueness check

        Raises:
            ValueError: If public key is already used by another device
        """
        query = select(Device).where(
            Device.network_id == network_id, Device.public_key == public_key
        )

        if exclude_device_id:
            query = query.where(Device.id != exclude_device_id)

        result = await self.db.execute(query)
        existing_device = result.scalar_one_or_none()

        if existing_device:
            raise ValueError(
                f"Public key is already used by device '{existing_device.name}'"
            )

    async def validate_external_endpoint_unique(
        self,
        external_host: str | None,
        external_port: int | None,
        exclude_device_id: str | None = None,
    ) -> None:
        """Validate that external endpoint is globally unique across all devices.

        Args:
            external_host: The effective external host to validate (None is valid)
            external_port: The external port to validate (None is valid)
            exclude_device_id: ID of device to exclude from uniqueness check

        Raises:
            ValueError: If external endpoint is already used by another device
        """
        if external_host is None or external_port is None:
            return

        query = (
            select(Device)
            .join(Location, Device.location_id == Location.id)
            .where(Device.external_endpoint_port == external_port)
            .where(
                sa.func.coalesce(Device.external_endpoint_host, Location.external_endpoint)
                == external_host
            )
        )

        if exclude_device_id:
            query = query.where(Device.id != exclude_device_id)

        result = await self.db.execute(query)
        existing_device = result.scalar_one_or_none()

        if existing_device:
            raise ValueError(
                f"External endpoint '{external_host}:{external_port}' is already used by device '{existing_device.name}'"
            )

    async def validate_internal_endpoint_unique(
        self,
        internal_host: str | None,
        internal_port: int | None,
        location_id: str,
        exclude_device_id: str | None = None,
    ) -> None:
        """Validate that internal endpoint is unique within a location.

        Args:
            internal_host: The internal endpoint host to validate (None is valid)
            internal_port: The internal endpoint port to validate (None is valid)
            location_id: ID of the location to check within
            exclude_device_id: ID of device to exclude from uniqueness check

        Raises:
            ValueError: If internal endpoint is already used by another device in the same location
        """
        if internal_host is None or internal_port is None:
            return

        query = select(Device).where(
            Device.location_id == location_id,
            Device.internal_endpoint_host == internal_host,
            Device.internal_endpoint_port == internal_port,
        )

        if exclude_device_id:
            query = query.where(Device.id != exclude_device_id)

        result = await self.db.execute(query)
        existing_device = result.scalar_one_or_none()

        if existing_device:
            raise ValueError(
                f"Internal endpoint '{internal_host}:{internal_port}' is already used by device '{existing_device.name}' in the same location"
            )
