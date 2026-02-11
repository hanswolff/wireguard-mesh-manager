"""Service for generating device configurations."""

from __future__ import annotations

import inspect as py_inspect
import ipaddress
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import inspect, select
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.attributes import NO_VALUE

from app.database.models import APIKey, Device, DevicePeerLink, Location, WireGuardNetwork
from app.schemas.device_config import (
    DeviceConfigResponse,
    DeviceConfiguration,
    MobileConfig,
    WireGuardInterfaceConfig,
    WireGuardPeerConfig,
)
from app.utils.api_key import (
    BCRYPT_HASH_PREFIX,
    SHA256_HASH_LENGTH,
    _verify_sha256_key,
    compute_api_key_fingerprint,
    verify_api_key,
)
from app.utils.key_management import (
    decrypt_device_dek_from_json,
    decrypt_preshared_key_from_json,
    decrypt_private_key_from_json,
    decrypt_private_key_with_dek,
    decrypt_preshared_key_with_dek,
)
from app.utils.master_password import get_master_password

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class DeviceConfigService:
    """Service for generating device configurations."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize the service."""
        self.db = db

    async def generate_device_config(
        self,
        device: Device,
        device_private_key: str,
        format_type: str = "wg",
        platform: str | None = None,
        device_dek: str | None = None,
        include_preshared_keys: bool = True,
    ) -> DeviceConfigResponse:
        """Generate a WireGuard configuration for a device in mesh topology.

        For mesh topology, the device configuration includes all other devices
        in the network as peers. Endpoint selection follows these rules:
        - Same location: use peer's internal endpoint
        - Different location: use peer's external endpoint

        Args:
            device: Device model with relationships loaded
            device_private_key: Decrypted private key for the device
            format_type: Configuration format ('wg', 'json', 'mobile')
            platform: Mobile platform for optimized config
            device_dek: Decrypted device DEK for API-key access to network PSKs

        Returns:
            DeviceConfigResponse with generated configuration

        Raises:
            ValueError: If device is not associated with a network
        """
        allowed_formats = {"wg", "json", "mobile"}
        if format_type not in allowed_formats:
            raise ValueError(f"Unsupported format '{format_type}'")
        if format_type == "mobile" and not platform:
            raise ValueError("Mobile configuration requires a platform value")

        # Get network information
        network = device.network
        if not network:
            raise ValueError("Device must be associated with a network")

        # Validate address placement and preserve network prefix
        interface_address = self._build_interface_address(device, network)

        # Merge interface properties from hierarchy (network -> location -> device)
        merged_properties = self._merge_interface_properties(
            network, device.location, device
        )

        # Build interface configuration
        # MTU can be overridden by interface_properties (e.g., device-level MTU)
        mtu = merged_properties.pop("MTU", None) if merged_properties else None

        # Handle various MTU formats: None, empty string, string int, or int
        if mtu is not None:
            # Try to convert string representation to integer
            try:
                mtu = int(mtu) if mtu != '' else None
            except (ValueError, TypeError):
                mtu = None

        # Fall back to network MTU if no valid MTU provided
        if mtu is None:
            mtu = network.mtu

        # Determine ListenPort from device endpoints (prefer internal port)
        # ListenPort is the port on which this device listens for incoming WireGuard connections
        listen_port = None
        if device.internal_endpoint_port:
            listen_port = device.internal_endpoint_port
        elif device.external_endpoint_port:
            listen_port = device.external_endpoint_port

        # Check if ListenPort is overridden in interface_properties
        if merged_properties and "ListenPort" in merged_properties:
            try:
                listen_port_override = merged_properties.pop("ListenPort")
                # Handle string, int, or None
                if listen_port_override is not None:
                    if isinstance(listen_port_override, str):
                        listen_port_override = int(listen_port_override) if listen_port_override != "" else None
                    if 1 <= listen_port_override <= 65535:
                        listen_port = int(listen_port_override)
            except (ValueError, TypeError):
                pass  # Keep the original listen_port if conversion fails

        interface_config = WireGuardInterfaceConfig(
            private_key=device_private_key,
            address=interface_address,
            dns=network.dns_servers,
            mtu=mtu,
            listen_port=listen_port,
            interface_properties=merged_properties if merged_properties else None,
        )

        # Generate peer configurations for mesh topology
        peer_configs = await self._generate_peer_configs(
            device, device_dek=device_dek, include_preshared_keys=include_preshared_keys
        )

        # Generate configuration based on requested format
        if format_type == "json":
            configuration: str | DeviceConfiguration | MobileConfig = (
                DeviceConfiguration(
                    interface=interface_config,
                    peers=peer_configs,
                )
            )
        elif format_type == "mobile" and platform:
            # For mobile configs, we use the first peer as the "primary" peer
            # since mobile platforms typically expect a single server peer
            if peer_configs:
                configuration = self._generate_mobile_config(
                    interface_config, peer_configs[0], device.name, platform
                )
            else:
                # No peers available - still generate config with empty peers
                configuration = self._generate_mobile_config(
                    interface_config,
                    WireGuardPeerConfig(
                        public_key="<no_peer>",
                        allowed_ips="0.0.0.0/0",
                        endpoint=None,
                    ),
                    device.name,
                    platform,
                )
        else:  # wg format (default)
            configuration = self._generate_wg_config(
                interface_config, peer_configs, device.name
            )

        return DeviceConfigResponse(
            device_id=device.id,
            device_name=device.name,
            network_name=network.name,
            configuration=configuration,
            format=format_type,
            created_at=datetime.now(UTC).isoformat(),
        )

    def _build_interface_address(
        self, device: Device, network: WireGuardNetwork
    ) -> str:
        """Construct the interface address using the network CIDR prefix."""
        network_cidr = ipaddress.ip_network(network.network_cidr, strict=False)

        if not device.wireguard_ip:
            raise ValueError("Device has no WireGuard IP address")

        device_ip = ipaddress.ip_address(device.wireguard_ip)

        if device_ip not in network_cidr:
            raise ValueError(
                f"Device IP {device.wireguard_ip} is not within network {network.network_cidr}"
            )

        return f"{device_ip}/{network_cidr.prefixlen}"

    def _generate_wg_config(
        self,
        interface: WireGuardInterfaceConfig,
        peers: list[WireGuardPeerConfig],
        device_name: str | None = None,
    ) -> str:
        """Generate standard WireGuard configuration format with mesh topology peers.

        Args:
            interface: Interface configuration
            peers: List of peer configurations for mesh topology

        Returns:
            WireGuard configuration string
        """
        lines = []
        if device_name:
            lines.append(f"# {device_name}")
        lines.append("[Interface]")
        lines.append(f"PrivateKey = {interface.private_key}")
        lines.append(f"Address = {interface.address}")

        if interface.listen_port:
            lines.append(f"ListenPort = {interface.listen_port}")

        if interface.dns:
            lines.append(f"DNS = {interface.dns}")

        if interface.mtu:
            lines.append(f"MTU = {interface.mtu}")

        # Add custom interface properties
        if interface.interface_properties:
            for key, value in interface.interface_properties.items():
                # Skip standard properties that are already handled (but allow mtu from properties)
                # Note: mtu is handled separately above, but we don't filter it here in case
                # it was set directly in properties without going through the merge logic
                if key.lower() in ["privatekey", "address", "dns"]:
                    continue
                # Handle multi-line values like PostUp/PostDown scripts
                if "\n" in str(value):
                    # WireGuard expects each line to repeat the key.
                    for line in str(value).split("\n"):
                        lines.append(f"{key} = {line}")
                else:
                    lines.append(f"{key} = {value}")

        # Add all peer configurations for mesh topology
        for peer in peers:
            lines.append("")  # Empty line before each peer
            if peer.name:
                lines.append(f"# {peer.name}")
            lines.append("[Peer]")
            lines.append(f"PublicKey = {peer.public_key}")

            if peer.preshared_key:
                lines.append(f"PresharedKey = {peer.preshared_key}")

            lines.append(f"AllowedIPs = {peer.allowed_ips}")

            if peer.endpoint:
                lines.append(f"Endpoint = {peer.endpoint}")

            if peer.persistent_keepalive is not None:
                lines.append(f"PersistentKeepalive = {peer.persistent_keepalive}")

            if peer.peer_properties:
                for key in sorted(peer.peer_properties.keys()):
                    value = peer.peer_properties[key]
                    if value is None:
                        continue
                    if "\n" in str(value):
                        for line in str(value).split("\n"):
                            lines.append(f"{key} = {line}")
                    else:
                        lines.append(f"{key} = {value}")

        return "\n".join(lines)

    async def _generate_peer_configs(
        self,
        device: Device,
        *,
        device_dek: str | None = None,
        include_preshared_keys: bool = True,
    ) -> list[WireGuardPeerConfig]:
        """Generate peer configurations for all other devices in the network.

        Args:
            device: The device to generate configuration for

        Returns:
            List of peer configurations for mesh topology
        """
        # Get all devices in the network
        network_devices = await self._get_network_devices(device)

        # Load directional link properties for this device
        peer_link_data = await self._get_peer_link_properties(device)

        # Generate peer configs for all other enabled devices
        peer_configs = []
        for other_device in network_devices:
            if self._should_include_peer(device, other_device):
                link_data = peer_link_data.get(other_device.id) or {}
                properties = link_data.get("properties")
                persistent_keepalive = device.network.persistent_keepalive
                peer_properties = None
                if properties:
                    if "PersistentKeepalive" in properties:
                        persistent_keepalive = properties.get("PersistentKeepalive")
                    peer_properties = {
                        key: value
                        for key, value in properties.items()
                        if key != "PersistentKeepalive"
                    } or None
                same_location = self._is_same_location(device, other_device)
                peer_config = WireGuardPeerConfig(
                    name=other_device.name,
                    public_key=other_device.public_key,
                    allowed_ips=f"{other_device.wireguard_ip}/32",
                    endpoint=self._get_device_endpoint(device, other_device),
                    persistent_keepalive=persistent_keepalive,
                    preshared_key=await self._get_preshared_key_for_pair(
                        device,
                        other_device,
                        device_dek=device_dek,
                        include_preshared_keys=include_preshared_keys,
                        same_location=same_location,
                        link_data=link_data,
                    ),
                    peer_properties=peer_properties,
                )
                peer_configs.append(peer_config)

        # Sort peers by IP address for deterministic output
        peer_configs.sort(key=self._peer_sort_key)

        return peer_configs

    def _peer_sort_key(
        self, peer: WireGuardPeerConfig
    ) -> tuple[int, bytes | str]:
        """Sort peers by IP address for deterministic output."""
        allowed_ips = (peer.allowed_ips or "").split(",")[0].strip()
        ip_str = allowed_ips.split("/")[0]
        try:
            ip = ipaddress.ip_address(ip_str)
            return (ip.version, ip.packed)
        except ValueError:
            return (0, allowed_ips)

    async def _get_peer_link_properties(
        self, device: Device
    ) -> dict[str, dict[str, Any] | None]:
        """Load directional peer properties and preshared keys for the device."""
        if not device.network_id:
            return {}

        network = getattr(device, "network", None)
        if network is not None and not isinstance(network, WireGuardNetwork):
            links = getattr(network, "device_peer_links", None)
            if isinstance(links, list):
                return self._build_peer_link_data(links, device.id)

        if network is not None:
            state = inspect(network, raiseerr=False)
            if state is not None and "device_peer_links" in state.attrs:
                links_attr = state.attrs.device_peer_links
                if links_attr.loaded_value is not NO_VALUE:
                    return self._build_peer_link_data(
                        list(links_attr.value or []), device.id
                    )
            if state is None:
                links = getattr(network, "device_peer_links", None)
                if isinstance(links, list):
                    return self._build_peer_link_data(links, device.id)

        try:
            result = await self.db.execute(
                select(DevicePeerLink).where(
                    DevicePeerLink.network_id == device.network_id,
                    DevicePeerLink.from_device_id == device.id,
                )
            )
            scalars = result.scalars()
            if py_inspect.isawaitable(scalars):
                scalars = await scalars
            items = scalars.all()
            if py_inspect.isawaitable(items):
                items = await items
            return self._build_peer_link_data(list(items), device.id)
        except (AttributeError, TypeError):
            # Handle cases where db is a mock or device_peer_links table doesn't exist
            return {}

    def _build_peer_link_data(
        self, links: list[DevicePeerLink], from_device_id: str
    ) -> dict[str, dict[str, Any] | None]:
        data: dict[str, dict[str, Any] | None] = {}
        for link in links:
            if link.from_device_id != from_device_id:
                continue
            preshared_key_encrypted = (
                link.preshared_key_encrypted
                if isinstance(link.preshared_key_encrypted, str)
                else None
            )
            preshared_key_encrypted_dek = (
                link.preshared_key_encrypted_dek
                if isinstance(link.preshared_key_encrypted_dek, str)
                else None
            )
            data[link.to_device_id] = {
                "properties": link.properties or {},
                "preshared_key_encrypted": preshared_key_encrypted,
                "preshared_key_encrypted_dek": preshared_key_encrypted_dek,
            }
        return data

    def _is_same_location(self, device: Device, peer_device: Device) -> bool:
        """Return True when both devices share the same location."""
        return (
            device.location
            and peer_device.location
            and device.location.id == peer_device.location.id
        )

    async def _get_network_devices(self, device: Device) -> list[Device]:
        """Get all devices in the same network as the given device.

        Args:
            device: Device to get network devices for

        Returns:
            List of all devices in the network
        """
        if not device.network_id:
            return []

        network = getattr(device, "network", None)
        if network is not None and not isinstance(network, WireGuardNetwork):
            devices = getattr(network, "devices", None)
            if isinstance(devices, list):
                return devices

        if network is not None:
            state = inspect(network, raiseerr=False)
            if state is not None and "devices" in state.attrs:
                devices_attr = state.attrs.devices
                if devices_attr.loaded_value is not NO_VALUE:
                    return list(devices_attr.value or [])
            if state is None:
                devices = getattr(network, "devices", None)
                if isinstance(devices, list):
                    return devices

        result = await self.db.execute(
            select(Device)
            .options(joinedload(Device.location))
            .where(Device.network_id == device.network_id)
        )
        scalars = result.scalars()
        if py_inspect.isawaitable(scalars):
            scalars = await scalars
        items = scalars.all()
        if py_inspect.isawaitable(items):
            items = await items
        return list(items)

    def _should_include_peer(self, device: Device, peer_device: Device) -> bool:
        """Determine if a peer should be included in device configuration.

        Args:
            device: The device being configured
            peer_device: Potential peer device

        Returns:
            True if peer should be included, False otherwise
        """
        if device.id == peer_device.id:
            return False

        if not peer_device.enabled:
            return False

        if not peer_device.wireguard_ip:
            return False

        return peer_device.public_key is not None

    def _get_device_endpoint(self, device: Device, peer_device: Device) -> str | None:
        """Get the endpoint for a peer device based on location rules.

        Endpoint selection rules:
        - Same location: use peer's internal endpoint
        - Different location: use peer's external endpoint

        Args:
            device: The device being configured
            peer_device: The peer device to get endpoint for

        Returns:
            Endpoint string (host:port) or None if no endpoint available
        """
        # Check if devices are in the same location
        same_location = (
            device.location
            and peer_device.location
            and device.location.id == peer_device.location.id
        )

        if same_location:
            # Use internal endpoint for same location
            internal_endpoint = self._build_internal_endpoint(peer_device)
            if internal_endpoint:
                return internal_endpoint
            # Fall back to external endpoint if no internal endpoint
            return self._build_external_endpoint(peer_device)
        else:
            # Use external endpoint for different locations
            return self._build_external_endpoint(peer_device)

    def _build_external_endpoint(self, device: Device) -> str | None:
        """Build external endpoint from device fields with location fallback."""
        host = device.external_endpoint_host
        port = device.external_endpoint_port
        if host and port:
            return self._format_host_port(host, port)
        if port and not host and device.location and device.location.external_endpoint:
            return self._format_host_port(device.location.external_endpoint, port)
        return None

    def _build_internal_endpoint(self, device: Device) -> str | None:
        """Build internal endpoint from device fields."""
        host = device.internal_endpoint_host
        port = device.internal_endpoint_port
        if host and port:
            return self._format_host_port(host, port)
        if device.location and device.location.internal_endpoint:
            try:
                from app.utils.validation import validate_endpoint

                location_host, location_port = validate_endpoint(
                    device.location.internal_endpoint
                )
                return self._format_host_port(location_host, location_port)
            except Exception:
                return None
        return None

    def _format_host_port(self, host: str, port: int) -> str:
        """Format host:port with IPv6 bracket normalization."""
        cleaned_host = host.strip()
        if cleaned_host.startswith("[") and cleaned_host.endswith("]"):
            return f"{cleaned_host}:{port}"
        try:
            ip_addr = ipaddress.ip_address(cleaned_host)
            if ip_addr.version == 6:
                return f"[{cleaned_host}]:{port}"
        except ValueError:
            pass
        return f"{cleaned_host}:{port}"

    async def _get_preshared_key_for_pair(
        self,
        device: Device,
        peer_device: Device,
        *,
        device_dek: str | None = None,
        include_preshared_keys: bool = True,
        same_location: bool = False,
        link_data: dict[str, Any] | None = None,
    ) -> str | None:
        """Get the preshared key for a device pair.

        Priority order:
        1. Per-peer preshared key (directional link)
        2. Location preshared key for same-location peers
        3. Network preshared key for cross-location peers
        4. Device-level preshared key (legacy fallback)
        5. None (no preshared key)

        Args:
            device: The device being configured
            peer_device: The peer device
            device_dek: Decrypted device DEK for API-key access to network PSKs

        Returns:
            Preshared key string or None
        """
        if not include_preshared_keys:
            return None

        link_data = link_data or {}
        link_preshared_key = link_data.get("preshared_key_encrypted")
        link_preshared_key_dek = link_data.get("preshared_key_encrypted_dek")
        if link_preshared_key or link_preshared_key_dek:
            if device_dek:
                if link_preshared_key_dek:
                    return decrypt_preshared_key_with_dek(
                        link_preshared_key_dek, device_dek
                    )
                raise ValueError(
                    "Per-peer preshared key not available for API key access"
                )
            master_password = get_master_password(require_cache=True)
            return decrypt_preshared_key_from_json(
                link_preshared_key, master_password
            )

        # Then check for location-level preshared key
        location = device.location
        if (
            same_location
            and location
            and getattr(location, "preshared_key_encrypted", None)
        ):
            if device_dek and device.location_preshared_key_encrypted:
                return decrypt_preshared_key_with_dek(
                    device.location_preshared_key_encrypted, device_dek
                )
            if device_dek:
                raise ValueError(
                    "Location preshared key not available for API key access"
                )
            master_password = get_master_password(require_cache=True)
            return decrypt_preshared_key_from_json(
                location.preshared_key_encrypted, master_password
            )

        # Then check for network-level preshared key
        network = device.network
        if network and getattr(network, "preshared_key_encrypted", None):
            if device_dek and device.network_preshared_key_encrypted:
                return decrypt_preshared_key_with_dek(
                    device.network_preshared_key_encrypted, device_dek
                )
            if device_dek:
                raise ValueError(
                    "Network preshared key not available for API key access"
                )
            master_password = get_master_password(require_cache=True)
            return decrypt_preshared_key_from_json(
                network.preshared_key_encrypted, master_password
            )

        if device.preshared_key_encrypted:
            if device_dek:
                raise ValueError(
                    "Device-level preshared keys require master password access"
                )
            return await self.decrypt_preshared_key(device)

        return None

    def _merge_interface_properties(
        self,
        network: WireGuardNetwork,
        location: Location | None,
        device: Device,
    ) -> dict[str, Any] | None:
        """Merge interface properties from hierarchy (network -> location -> device).

        Device properties override location properties, which override network properties.

        Args:
            network: Network model
            location: Location model (optional)
            device: Device model

        Returns:
            Merged interface properties or None if no properties are configured
        """
        merged: dict[str, Any] = {}

        # Start with network properties
        if network.interface_properties:
            merged.update(network.interface_properties)

        # Override with location properties
        if location and location.interface_properties:
            merged.update(location.interface_properties)

        # Override with device properties
        if device.interface_properties:
            merged.update(device.interface_properties)

        return merged if merged else None

    def _generate_mobile_config(
        self,
        interface: WireGuardInterfaceConfig,
        peer: WireGuardPeerConfig,
        device_name: str,
        platform: str,
    ) -> MobileConfig:
        """Generate mobile-optimized configuration."""
        # Parse DNS servers
        dns_servers = []
        if interface.dns:
            dns_servers = [dns.strip() for dns in interface.dns.split(",")]

        # Parse address
        addresses = [interface.address]

        # Parse allowed IPs
        allowed_ips = []
        if peer.allowed_ips:
            allowed_ips = [ip.strip() for ip in peer.allowed_ips.split(",")]

        return MobileConfig(
            name=f"{device_name} - {platform.title()}",
            addresses=addresses,
            dns=dns_servers,
            mtu=interface.mtu,
            public_key=peer.public_key,
            allowed_ips=allowed_ips,
            endpoint=peer.endpoint,
            persistent_keepalive=peer.persistent_keepalive,
        )

    async def validate_device_access(
        self,
        device_id: str,
        api_key: str | None = None,
        source_ip: str | None = None,
    ) -> tuple[Device, APIKey | None, bool, str | None]:
        """Validate if a device can be accessed for configuration retrieval.

        Args:
            device_id: ID of the device to access
            api_key: API key for authentication
            source_ip: Source IP address for allowlist validation

        Returns:
            Tuple of (device_model, matching_api_key, is_valid_access, denied_reason)

        Raises:
            ValueError: If device is not found
        """
        device = await self._get_device_with_keys(device_id)

        if not api_key:
            return device, None, False, "missing_api_key"

        # Find the specific API key being used
        matching_key = await self._find_matching_api_key(device, api_key)
        if not matching_key:
            return device, None, False, "invalid_api_key"

        # Validate source IP against the specific key's allowlist
        if matching_key.allowed_ip_ranges:
            if not source_ip:
                return device, matching_key, False, "missing_source_ip"

            try:
                if not self._is_ip_in_key_allowlist(source_ip, matching_key):
                    return device, matching_key, False, "source_ip_not_allowed"
            except ValueError:
                return device, matching_key, False, "invalid_source_ip"

        await self._update_api_key_last_used(matching_key)
        return device, matching_key, True, None

    async def _validate_api_key(self, device: Device, api_key: str) -> bool:
        """Validate an API key against the device's enabled keys."""
        matching_key = await self._find_matching_api_key(device, api_key)
        return matching_key is not None

    async def _validate_source_ip(self, device: Device, source_ip: str) -> bool:
        """Validate a source IP against any enabled API key allowlist."""
        if not device.api_keys or not source_ip:
            return False

        try:
            source_addr = ipaddress.ip_address(source_ip)
        except ValueError:
            return False

        for key_obj in device.api_keys:
            if not key_obj.enabled or not self._is_api_key_valid(key_obj):
                continue

            if not key_obj.allowed_ip_ranges:
                return True

            if self._is_ip_in_ranges(source_addr, key_obj.allowed_ip_ranges):
                return True

        return False

    async def _get_device_with_keys(self, device_id: str) -> Device:
        """Query device with all required relationships loaded."""
        result = await self.db.execute(
            select(Device)
            .options(
                joinedload(Device.network).joinedload(WireGuardNetwork.locations),
                joinedload(Device.location),
                joinedload(Device.api_keys),
            )
            .where(Device.id == device_id, Device.enabled.is_(True))
        )

        device = result.unique().scalar_one_or_none()
        if not device:
            raise ValueError("Device not found or disabled")

        return device

    def _verify_api_key_hash(self, api_key: str, key_hash: str) -> bool:
        """Verify API key hashes, supporting legacy SHA-256 for device access."""
        if key_hash.startswith(BCRYPT_HASH_PREFIX):
            try:
                return verify_api_key(api_key, key_hash)
            except RuntimeError:
                return False

        if len(key_hash) == SHA256_HASH_LENGTH:
            return _verify_sha256_key(api_key, key_hash)

        return False

    async def _find_matching_api_key(
        self, device: Device, api_key: str
    ) -> APIKey | None:
        """Find the specific API key that matches the provided key."""
        if api_key:
            try:
                fingerprint = compute_api_key_fingerprint(api_key)
            except ValueError:
                fingerprint = None

            if fingerprint:
                result = await self.db.execute(
                    select(APIKey).where(
                        APIKey.device_id == device.id,
                        APIKey.key_fingerprint == fingerprint,
                        APIKey.enabled.is_(True),
                    )
                )
                candidate = result.scalar_one_or_none()
                if candidate and self._is_api_key_valid(candidate):
                    if self._verify_api_key_hash(api_key, candidate.key_hash):
                        return candidate

        if not device.api_keys:
            return None

        for key_obj in device.api_keys:
            if key_obj.key_fingerprint:
                continue
            if (
                key_obj.enabled
                and self._verify_api_key_hash(api_key, key_obj.key_hash)
                and self._is_api_key_valid(key_obj)
            ):
                return key_obj

        return None

    def _is_api_key_valid(self, api_key: APIKey) -> bool:
        """Check if an API key is not expired."""
        expires_at = api_key.expires_at
        if expires_at is None:
            return True

        if expires_at.tzinfo is None:
            expires_at_with_tz = expires_at.replace(tzinfo=UTC)
            return expires_at_with_tz > datetime.now(UTC)

        return expires_at > datetime.now(UTC)

    def _is_ip_in_key_allowlist(self, source_ip: str, api_key: APIKey) -> bool:
        """Check if source IP is in the specific API key's allowlist."""
        if not api_key.allowed_ip_ranges:
            return True  # No restriction if no ranges configured

        if not source_ip:
            raise ValueError("Source IP required for allowlist validation")

        try:
            source_addr = ipaddress.ip_address(source_ip)
        except ValueError as exc:
            raise ValueError("Invalid source IP for allowlist validation") from exc

        return self._is_ip_in_ranges(source_addr, api_key.allowed_ip_ranges)

    def _is_ip_in_ranges(
        self,
        source_ip: ipaddress.IPv4Address | ipaddress.IPv6Address,
        allowed_ranges: str,
    ) -> bool:
        """Check if IP is in any of the allowed ranges."""
        for range_str in allowed_ranges.split(","):
            range_str = range_str.strip()
            if not range_str:
                continue

            try:
                if "/" in range_str:
                    network = ipaddress.ip_network(range_str, strict=False)
                    if source_ip in network:
                        return True
                else:
                    allowed_ip = ipaddress.ip_address(range_str)
                    if source_ip == allowed_ip:
                        return True
            except ValueError:
                continue

        return False

    async def _update_api_key_last_used(self, api_key: APIKey | None) -> None:
        """Update the last used timestamp for the matching API key."""
        if not api_key:
            return

        now = datetime.now(UTC)
        api_key.last_used_at = now
        await self.db.commit()

    async def decrypt_device_private_key(
        self,
        device: Device,
        master_password: str | None = None,
    ) -> str:
        """Decrypt a device's private key using the master password.

        Args:
            device: Device model with encrypted private key
            master_password: Master password for decryption (optional, will use cache if not provided)

        Returns:
            Decrypted private key

        Raises:
            ValueError: If decryption fails or required credentials are invalid
        """
        if not device.private_key_encrypted:
            raise ValueError("Device has no encrypted private key")

        resolved_password = get_master_password(provided_password=master_password)

        if device.device_dek_encrypted_master:
            device_dek = decrypt_device_dek_from_json(
                device.device_dek_encrypted_master, resolved_password
            )
            return decrypt_private_key_with_dek(
                device.private_key_encrypted, device_dek
            )

        return decrypt_private_key_from_json(
            device.private_key_encrypted, resolved_password
        )

    async def decrypt_device_private_key_with_api_key(
        self,
        device: Device,
        api_key: str,
        api_key_record: APIKey | None = None,
    ) -> str:
        """Decrypt a device's private key using an API key-derived KEK.

        Args:
            device: Device model with encrypted private key
            api_key: API key for device self-service decryption

        Returns:
            Decrypted private key

        Raises:
            ValueError: If decryption fails or required credentials are invalid
        """
        if not device.private_key_encrypted:
            raise ValueError("Device has no encrypted private key")
        if not api_key:
            raise ValueError("API key is required for device access")
        device_dek = await self.decrypt_device_dek_with_api_key(
            device, api_key, api_key_record=api_key_record
        )
        return decrypt_private_key_with_dek(device.private_key_encrypted, device_dek)

    async def decrypt_device_private_key_with_dek(
        self, device: Device, device_dek: str
    ) -> str:
        """Decrypt a device's private key using a decrypted device DEK."""
        if not device.private_key_encrypted:
            raise ValueError("Device has no encrypted private key")
        if not device_dek:
            raise ValueError("Device DEK is required for device access")
        return decrypt_private_key_with_dek(device.private_key_encrypted, device_dek)

    async def decrypt_device_dek_with_api_key(
        self,
        device: Device,
        api_key: str,
        api_key_record: APIKey | None = None,
    ) -> str:
        """Decrypt a device's DEK using an API key-derived KEK."""
        if not api_key:
            raise ValueError("API key is required for device access")

        matching_key = api_key_record or await self._find_matching_api_key(
            device, api_key
        )
        encrypted_dek = None
        if matching_key and matching_key.device_dek_encrypted:
            encrypted_dek = matching_key.device_dek_encrypted
        elif device.device_dek_encrypted_api_key:
            encrypted_dek = device.device_dek_encrypted_api_key

        if not encrypted_dek:
            raise ValueError("Device DEK is not available for API key access")

        return decrypt_device_dek_from_json(encrypted_dek, api_key)

    async def decrypt_preshared_key(
        self, device: Device, master_password: str | None = None
    ) -> str | None:
        """Decrypt a device's preshared key using the master password.

        Args:
            device: Device model with encrypted preshared key
            master_password: Master password for decryption (optional, will use cache if not provided)

        Returns:
            Decrypted preshared key, or None if no preshared key is set

        Raises:
            ValueError: If decryption fails or master password is invalid
        """
        # Get master password from cache or use provided password
        resolved_password = get_master_password(provided_password=master_password)

        return decrypt_preshared_key_from_json(
            device.preshared_key_encrypted, resolved_password
        )
