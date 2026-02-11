"""Service for export and import operations."""

from __future__ import annotations

import json
import zipfile
from datetime import UTC, datetime
from io import BytesIO
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database.models import Device, Location, WireGuardNetwork
from app.exceptions import BusinessRuleViolationError
from app.schemas.device_config import DeviceConfiguration, MobileConfig
from app.schemas.export import (
    DeviceExport,
    ExportData,
    ExportMetadata,
    LocationExport,
    WireGuardNetworkExport,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.services.master_password import BaseMasterPasswordCache


def _serialize_config(config: Any, valid_types: list[type]) -> str:
    """Serialize configuration to JSON with deterministic ordering.

    Args:
        config: Configuration object to serialize
        valid_types: List of valid Pydantic model types that have model_dump_json method

    Returns:
        JSON string with proper formatting
    """
    if any(isinstance(config, valid_type) for valid_type in valid_types):
        return config.model_dump_json(indent=2)
    return json.dumps(config, indent=2, sort_keys=True)


class ExportImportService:
    """Service for managing export and import operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def export_networks(
        self,
        exported_by: str,
        description: str | None = None,
        network_ids: list[str] | None = None,
        include_encrypted_keys: bool = True,
    ) -> ExportData:
        """Export all networks with their locations and devices.

        Requires master password to be unlocked to export encrypted key material.
        """
        # Check if master password is unlocked before allowing export of encrypted keys
        from app.services.master_password import master_password_cache

        # Type annotation to help mypy
        cache: BaseMasterPasswordCache = master_password_cache

        if include_encrypted_keys and not cache.is_unlocked:
            raise BusinessRuleViolationError(
                "export_encrypted_keys",
                "Master password must be unlocked to export encrypted key material",
            )

        query = (
            select(WireGuardNetwork)
            .options(
                selectinload(WireGuardNetwork.locations),
                selectinload(WireGuardNetwork.devices).selectinload(Device.location),
            )
            .order_by(WireGuardNetwork.name)
        )
        if network_ids:
            query = query.where(WireGuardNetwork.id.in_(network_ids))

        result = await self.db.execute(query)
        networks = result.scalars().all()

        network_exports = [
            self._convert_network_to_export(
                network, include_encrypted_keys=include_encrypted_keys
            )
            for network in networks
        ]

        metadata = ExportMetadata(
            version="1.0",
            exported_at=datetime.now(UTC),
            exported_by=exported_by,
            description=description,
        )

        return ExportData(metadata=metadata, networks=network_exports)

    def _convert_network_to_export(
        self, network: WireGuardNetwork, include_encrypted_keys: bool = True
    ) -> WireGuardNetworkExport:
        """Convert a network to export format."""
        location_exports = [
            self._convert_location_to_export(location, include_encrypted_keys)
            for location in sorted(network.locations, key=lambda loc: loc.name)
        ]

        device_exports = [
            self._convert_device_to_export(
                device, include_encrypted_keys=include_encrypted_keys
            )
            for device in sorted(network.devices, key=lambda d: d.name)
        ]

        return WireGuardNetworkExport(
            name=network.name,
            description=network.description,
            network_cidr=network.network_cidr,
            dns_servers=network.dns_servers,
            mtu=network.mtu,
            persistent_keepalive=network.persistent_keepalive,
            private_key_encrypted=(
                network.private_key_encrypted if include_encrypted_keys else None
            ),
            public_key=network.public_key,
            preshared_key_encrypted=(
                network.preshared_key_encrypted if include_encrypted_keys else None
            ),
            interface_properties=network.interface_properties,
            locations=location_exports,
            devices=device_exports,
        )

    def _convert_location_to_export(
        self, location: Location, include_encrypted_keys: bool = True
    ) -> LocationExport:
        """Convert a location to export format."""
        return LocationExport(
            name=location.name,
            description=location.description,
            external_endpoint=location.external_endpoint,
            internal_endpoint=location.internal_endpoint,
            preshared_key_encrypted=(
                location.preshared_key_encrypted if include_encrypted_keys else None
            ),
            interface_properties=location.interface_properties,
        )

    def _convert_device_to_export(
        self, device: Device, include_encrypted_keys: bool = True
    ) -> DeviceExport:
        """Convert a device to export format."""
        private_key_encrypted = (
            device.private_key_encrypted if include_encrypted_keys else "REDACTED"
        )
        device_dek_encrypted_master = (
            device.device_dek_encrypted_master
            if include_encrypted_keys
            else ("REDACTED" if device.device_dek_encrypted_master else None)
        )
        device_dek_encrypted_api_key = (
            device.device_dek_encrypted_api_key
            if include_encrypted_keys
            else ("REDACTED" if device.device_dek_encrypted_api_key else None)
        )
        preshared_key_encrypted = (
            device.preshared_key_encrypted if include_encrypted_keys else None
        )
        network_preshared_key_encrypted = (
            device.network_preshared_key_encrypted if include_encrypted_keys else None
        )
        location_preshared_key_encrypted = (
            device.location_preshared_key_encrypted if include_encrypted_keys else None
        )
        return DeviceExport(
            name=device.name,
            description=device.description,
            wireguard_ip=device.wireguard_ip,
            private_key_encrypted=private_key_encrypted,
            device_dek_encrypted_master=device_dek_encrypted_master,
            device_dek_encrypted_api_key=device_dek_encrypted_api_key,
            public_key=device.public_key,
            preshared_key_encrypted=preshared_key_encrypted,
            network_preshared_key_encrypted=network_preshared_key_encrypted,
            location_preshared_key_encrypted=location_preshared_key_encrypted,
            enabled=device.enabled,
            location_name=device.location.name,
            interface_properties=device.interface_properties,
        )

    async def import_networks(
        self,
        export_data: ExportData,
        imported_by: str,
        overwrite_existing: bool = False,
    ) -> dict[str, Any]:
        """Import networks from export data."""
        self._validate_export_version(export_data.metadata.version)

        results = {
            "networks_created": 0,
            "networks_updated": 0,
            "locations_created": 0,
            "devices_created": 0,
            "errors": [],
        }

        for network_export in export_data.networks:
            await self._import_single_network(
                network_export, results, overwrite_existing
            )

        return results

    def _validate_export_version(self, version: str) -> None:
        """Validate the export data version."""
        if version != "1.0":
            raise BusinessRuleViolationError(
                "export_version", f"Unsupported export version: {version}"
            )

    async def _import_single_network(
        self,
        network_export: WireGuardNetworkExport,
        results: dict[str, Any],
        overwrite: bool,
    ) -> None:
        """Import a single network with its locations and devices."""
        try:
            network = await self._get_or_create_network(
                network_export, results, overwrite
            )
            if network is None:  # Skip due to conflict
                return
            location_map = await self._import_locations(
                network.id, network_export.locations, results
            )
            await self._import_devices(
                network.id, location_map, network_export.devices, results
            )
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            results["errors"].append(
                f"Error importing network '{network_export.name}': {str(e)}"
            )

    async def _get_or_create_network(
        self,
        network_export: WireGuardNetworkExport,
        results: dict[str, Any],
        overwrite: bool,
    ) -> WireGuardNetwork | None:
        """Get existing network or create new one."""
        existing_network = await self._get_network_by_name(network_export.name)

        if existing_network:
            if not overwrite:
                results["errors"].append(
                    f"Network '{network_export.name}' already exists and overwrite is disabled"
                )
                return None

            await self._update_network(existing_network, network_export)
            results["networks_updated"] += 1
            return existing_network

        network = await self._create_network(network_export)
        results["networks_created"] += 1
        return network

    async def _import_locations(
        self,
        network_id: str,
        location_exports: list[LocationExport],
        results: dict[str, Any],
    ) -> dict[str, Location]:
        """Import locations for a network."""
        location_map = {}

        for location_export in location_exports:
            existing_location = await self._get_location_by_name(
                network_id, location_export.name
            )

            if existing_location:
                await self._update_location(existing_location, location_export)
                location_map[location_export.name] = existing_location
            else:
                location = await self._create_location(network_id, location_export)
                location_map[location_export.name] = location
                results["locations_created"] += 1

        return location_map

    async def _import_devices(
        self,
        network_id: str,
        location_map: dict[str, Location],
        device_exports: list[DeviceExport],
        results: dict[str, Any],
    ) -> None:
        """Import devices for a network."""
        for device_export in device_exports:
            if device_export.location_name not in location_map:
                results["errors"].append(
                    f"Device '{device_export.name}' references unknown location '{device_export.location_name}'"
                )
                continue

            location = location_map[device_export.location_name]
            existing_device = await self._get_device_by_public_key(
                network_id, device_export.public_key
            )

            if existing_device:
                await self._update_device(existing_device, device_export, location)
            else:
                await self._create_device(network_id, location.id, device_export)
                results["devices_created"] += 1

    async def _get_network_by_name(self, name: str) -> WireGuardNetwork | None:
        """Get a network by name."""
        result = await self.db.execute(
            select(WireGuardNetwork).where(WireGuardNetwork.name == name)
        )
        return result.scalar_one_or_none()

    async def _get_location_by_name(
        self, network_id: str, name: str
    ) -> Location | None:
        """Get a location by network ID and name."""
        result = await self.db.execute(
            select(Location).where(
                Location.network_id == network_id, Location.name == name
            )
        )
        return result.scalar_one_or_none()

    async def _get_device_by_public_key(
        self, network_id: str, public_key: str
    ) -> Device | None:
        """Get a device by network ID and public key."""
        result = await self.db.execute(
            select(Device).where(
                Device.network_id == network_id, Device.public_key == public_key
            )
        )
        return result.scalar_one_or_none()

    async def _create_network(
        self, network_export: WireGuardNetworkExport
    ) -> WireGuardNetwork:
        """Create a new network from export data."""
        network = WireGuardNetwork(
            name=network_export.name,
            description=network_export.description,
            network_cidr=network_export.network_cidr,
            dns_servers=network_export.dns_servers,
            mtu=network_export.mtu,
            persistent_keepalive=network_export.persistent_keepalive,
            private_key_encrypted=network_export.private_key_encrypted,
            public_key=network_export.public_key,
            preshared_key_encrypted=network_export.preshared_key_encrypted,
            interface_properties=network_export.interface_properties,
        )
        self.db.add(network)
        await self.db.flush()
        return network

    async def _update_network(
        self, network: WireGuardNetwork, network_export: WireGuardNetworkExport
    ) -> None:
        """Update an existing network from export data."""
        network.description = network_export.description
        network.network_cidr = network_export.network_cidr
        network.dns_servers = network_export.dns_servers
        network.mtu = network_export.mtu
        network.persistent_keepalive = network_export.persistent_keepalive
        network.private_key_encrypted = network_export.private_key_encrypted
        network.public_key = network_export.public_key
        network.preshared_key_encrypted = network_export.preshared_key_encrypted
        network.interface_properties = network_export.interface_properties

    async def _create_location(
        self, network_id: str, location_export: LocationExport
    ) -> Location:
        """Create a new location from export data."""
        location = Location(
            network_id=network_id,
            name=location_export.name,
            description=location_export.description,
            external_endpoint=location_export.external_endpoint,
            internal_endpoint=location_export.internal_endpoint,
            preshared_key_encrypted=location_export.preshared_key_encrypted,
            interface_properties=location_export.interface_properties,
        )
        self.db.add(location)
        await self.db.flush()
        return location

    async def _update_location(
        self, location: Location, location_export: LocationExport
    ) -> None:
        """Update an existing location from export data."""
        location.description = location_export.description
        location.external_endpoint = location_export.external_endpoint
        location.internal_endpoint = location_export.internal_endpoint
        location.preshared_key_encrypted = location_export.preshared_key_encrypted
        location.interface_properties = location_export.interface_properties

    async def _create_device(
        self, network_id: str, location_id: str, device_export: DeviceExport
    ) -> Device:
        """Create a new device from export data."""
        device = Device(
            network_id=network_id,
            location_id=location_id,
            name=device_export.name,
            description=device_export.description,
            wireguard_ip=device_export.wireguard_ip,
            private_key_encrypted=device_export.private_key_encrypted,
            device_dek_encrypted_master=device_export.device_dek_encrypted_master,
            device_dek_encrypted_api_key=device_export.device_dek_encrypted_api_key,
            public_key=device_export.public_key,
            preshared_key_encrypted=device_export.preshared_key_encrypted,
            network_preshared_key_encrypted=device_export.network_preshared_key_encrypted,
            location_preshared_key_encrypted=device_export.location_preshared_key_encrypted,
            enabled=device_export.enabled,
            interface_properties=device_export.interface_properties,
        )
        self.db.add(device)
        await self.db.flush()
        return device

    async def _update_device(
        self, device: Device, device_export: DeviceExport, location: Location
    ) -> None:
        """Update an existing device from export data."""
        device.location_id = location.id
        device.name = device_export.name
        device.description = device_export.description
        device.wireguard_ip = device_export.wireguard_ip
        device.private_key_encrypted = device_export.private_key_encrypted
        device.device_dek_encrypted_master = device_export.device_dek_encrypted_master
        device.device_dek_encrypted_api_key = device_export.device_dek_encrypted_api_key
        device.public_key = device_export.public_key
        device.preshared_key_encrypted = device_export.preshared_key_encrypted
        device.network_preshared_key_encrypted = (
            device_export.network_preshared_key_encrypted
        )
        device.location_preshared_key_encrypted = (
            device_export.location_preshared_key_encrypted
        )
        device.enabled = device_export.enabled
        device.interface_properties = device_export.interface_properties

    async def export_network_configs(
        self,
        network_id: str,
        format_type: str = "wg",
        include_preshared_keys: bool = False,
        platform: str | None = None,
    ) -> BytesIO:
        """Export all device configurations for a network as a ZIP file.

        Args:
            network_id: ID of the network to export
            format_type: Configuration format ('wg', 'json', 'mobile')
            include_preshared_keys: Whether to include preshared keys in configs
            platform: Mobile platform for optimized config (required for mobile format)

        Returns:
            BytesIO containing ZIP file with all device configurations

        Raises:
            ValueError: If network not found or master password cache is locked
        """
        from app.services.device_config import DeviceConfigService
        from app.utils.master_password import get_master_password

        if format_type == "mobile" and not platform:
            raise ValueError("Mobile configuration exports require a platform value")

        # Get network with devices and locations
        result = await self.db.execute(
            select(WireGuardNetwork)
            .options(
                selectinload(WireGuardNetwork.locations),
                selectinload(WireGuardNetwork.devices).selectinload(Device.location),
            )
            .where(WireGuardNetwork.id == network_id)
        )
        network = result.scalar_one_or_none()
        if not network:
            raise ValueError(f"Network with ID {network_id} not found")

        config_service = DeviceConfigService(self.db)
        zip_buffer = BytesIO()
        master_password = get_master_password(require_cache=True)

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # Add network summary
            summary = self._generate_network_summary(network)
            zip_file.writestr(f"{network.name}/README.txt", summary)

            # Add each device configuration
            for device in sorted(network.devices, key=lambda d: d.name):
                if not device.enabled:
                    continue  # Skip disabled devices

                try:
                    device_private_key = await config_service.decrypt_device_private_key(
                        device, master_password
                    )

                    # Generate configuration
                    config_response = await config_service.generate_device_config(
                        device=device,
                        device_private_key=device_private_key,
                        format_type=format_type,
                        platform=platform,
                        include_preshared_keys=include_preshared_keys,
                    )

                    # Determine filename and content based on format
                    if format_type == "wg":
                        filename = f"{device.name.replace(' ', '_')}.conf"
                        content = str(config_response.configuration)
                    elif format_type == "json":
                        filename = f"{device.name.replace(' ', '_')}.json"
                        content = _serialize_config(
                            config_response.configuration,
                            [DeviceConfiguration, MobileConfig],
                        )
                    elif format_type == "mobile":
                        filename = f"{device.name.replace(' ', '_')}_mobile.json"
                        content = _serialize_config(
                            config_response.configuration, [MobileConfig]
                        )
                    else:
                        raise ValueError(f"Unsupported format type: {format_type}")

                    zip_file.writestr(f"{network.name}/devices/{filename}", content)

                except Exception as e:
                    # Add error information for this device
                    error_content = (
                        f"Failed to generate config for device {device.name}: {str(e)}"
                    )
                    zip_file.writestr(
                        f"{network.name}/errors/{device.name.replace(' ', '_')}.txt",
                        error_content,
                    )

        zip_buffer.seek(0)
        return zip_buffer

    def _generate_network_summary(self, network: WireGuardNetwork) -> str:
        """Generate a summary text file for the network export."""
        lines = [
            f"Network: {network.name}",
            f"Description: {network.description or 'None'}",
            f"Network CIDR: {network.network_cidr}",
            "",
            "Configuration:",
            f"  DNS Servers: {network.dns_servers or 'None'}",
            f"  MTU: {network.mtu or 'Default'}",
            f"  Persistent Keepalive: {network.persistent_keepalive or 'Disabled'}",
            "",
            f"Locations: {len(network.locations)}",
            "",
        ]

        for location in sorted(network.locations, key=lambda loc: loc.name):
            lines.append(f"  - {location.name}")
            if location.external_endpoint:
                lines.append(f"    Endpoint: {location.external_endpoint}")
            if location.description:
                lines.append(f"    Description: {location.description}")

        lines.extend(
            [
                "",
                f"Devices: {len([d for d in network.devices if d.enabled])} enabled, "
                f"{len([d for d in network.devices if not d.enabled])} disabled",
                "",
            ]
        )

        for device in sorted(network.devices, key=lambda d: d.name):
            status = "enabled" if device.enabled else "disabled"
            lines.append(f"  - {device.name} ({device.wireguard_ip}) - {status}")
            if device.description:
                lines.append(f"    Description: {device.description}")
            if device.location:
                lines.append(f"    Location: {device.location.name}")

        lines.extend(
            [
                "",
                "Export Information:",
                f"  Exported at: {datetime.now(UTC).isoformat()}",
                "",
                "Files included:",
                "  - devices/*.conf or *.json: Individual device configurations",
                "  - errors/*.txt: Any errors encountered during export",
                "",
            ]
        )

        return "\n".join(lines)
