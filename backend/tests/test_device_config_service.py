"""Tests for device configuration service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.database.models import Device, DevicePeerLink, Location, WireGuardNetwork
from app.schemas.device_config import DeviceConfigResponse
from app.services.device_config import DeviceConfigService
from app.utils.key_management import encrypt_preshared_key


def _split_endpoint(endpoint: str | None) -> tuple[str | None, int | None]:
    if not endpoint:
        return None, None
    if ":" not in endpoint:
        return None, None
    host, port_str = endpoint.rsplit(":", 1)
    host = host.strip()
    port_str = port_str.strip()
    if not host or not port_str:
        return None, None
    try:
        port = int(port_str)
    except ValueError:
        return None, None
    return host, port


def _apply_device_endpoints(
    device: MagicMock, external_endpoint: str | None, internal_endpoint: str | None
) -> None:
    device.external_endpoint_host, device.external_endpoint_port = _split_endpoint(
        external_endpoint
    )
    device.internal_endpoint_host, device.internal_endpoint_port = _split_endpoint(
        internal_endpoint
    )


@pytest.fixture
def mock_db() -> AsyncMock:
    """Mock database session."""
    db = AsyncMock()
    return db


@pytest.fixture
def device_config_service(mock_db: AsyncMock) -> DeviceConfigService:
    """Create device config service with mock DB."""
    return DeviceConfigService(mock_db)


@pytest.fixture
def mock_device() -> Device:
    """Create mock device with mesh topology peers."""
    device = MagicMock(spec=Device)
    device.id = "123e4567-e89b-12d3-a456-426614174000"
    device.name = "Test Device"
    device.network_id = "456e7890-e89b-12d3-a456-426614174000"
    device.location_id = "789e0123-e89b-12d3-a456-426614174000"
    device.wireguard_ip = "10.0.0.2"
    device.public_key = "test_device_public_key"
    device.preshared_key_encrypted = None
    device.location_preshared_key_encrypted = None
    device.enabled = True
    _apply_device_endpoints(device, None, None)

    # Mock network
    device.network = MagicMock(spec=WireGuardNetwork)
    device.network.id = "456e7890-e89b-12d3-a456-426614174000"
    device.network.name = "Test Network"
    device.network.network_cidr = "10.0.0.0/24"
    device.network.public_key = "test_network_public_key"
    device.network.dns_servers = "8.8.8.8,8.8.4.4"
    device.network.mtu = 1420
    device.network.persistent_keepalive = 25
    device.network.preshared_key_encrypted = None
    device.network.device_peer_links = []

    # Mock location
    device.location = MagicMock(spec=Location)
    device.location.id = "789e0123-e89b-12d3-a456-426614174000"
    device.location.name = "Test Location"
    device.location.external_endpoint = "vpn.example.com:51820"
    device.location.internal_endpoint = None
    device.location.preshared_key_encrypted = None

    # Mock peer device for mesh topology
    peer1 = MagicMock(spec=Device)
    peer1.id = "peer-1-id"
    peer1.name = "Peer Device 1"
    peer1.wireguard_ip = "10.0.0.3"
    peer1.public_key = "peer1_public_key_1234567890123456789012"
    peer1.enabled = True
    peer1.preshared_key_encrypted = None
    _apply_device_endpoints(peer1, "peer1.example.com:51820", None)
    peer1.location = device.location  # Same location

    device.network.locations = [device.location]
    device.network.devices = [device, peer1]

    return device


@pytest.fixture
def mock_device_with_network_locations() -> Device:
    """Create mock device with network having multiple locations and peers."""
    device = MagicMock(spec=Device)
    device.id = "123e4567-e89b-12d3-a456-426614174000"
    device.name = "Test Device"
    device.network_id = "456e7890-e89b-12d3-a456-426614174000"
    device.location_id = "789e0123-e89b-12d3-a456-426614174000"  # Has location
    device.wireguard_ip = "10.0.0.2"
    device.public_key = "test_device_public_key"
    device.preshared_key_encrypted = None
    device.location_preshared_key_encrypted = None
    device.enabled = True
    _apply_device_endpoints(device, None, None)

    # Mock network with locations
    device.network = MagicMock(spec=WireGuardNetwork)
    device.network.id = "456e7890-e89b-12d3-a456-426614174000"
    device.network.name = "Test Network"
    device.network.network_cidr = "10.0.0.0/24"
    device.network.public_key = "test_network_public_key"
    device.network.dns_servers = "8.8.8.8,8.8.4.4"
    device.network.mtu = 1420
    device.network.persistent_keepalive = 25
    device.network.preshared_key_encrypted = None
    device.network.device_peer_links = []

    # Mock multiple locations on network
    location1 = MagicMock(spec=Location)
    location1.id = "789e0123-e89b-12d3-a456-426614174000"
    location1.name = "Location 1"
    location1.external_endpoint = "vpn1.example.com:51820"
    location1.internal_endpoint = "192.168.1.10:51820"
    location1.preshared_key_encrypted = None

    location2 = MagicMock(spec=Location)
    location2.id = "789e0123-e89b-12d3-a456-426614174001"
    location2.name = "Location 2"
    location2.external_endpoint = "vpn2.example.com:51820"
    location2.internal_endpoint = None
    location2.preshared_key_encrypted = None

    # Set device's location
    device.location = location1

    # Mock peer devices
    peer1 = MagicMock(spec=Device)
    peer1.id = "peer-1-id"
    peer1.name = "Peer Device 1"
    peer1.wireguard_ip = "10.0.0.3"
    peer1.public_key = "peer1_public_key_1234567890123456789012"
    peer1.enabled = True
    peer1.preshared_key_encrypted = None
    _apply_device_endpoints(peer1, "peer1.example.com:51820", "192.168.1.11:51820")
    peer1.location = location1  # Same location as device

    peer2 = MagicMock(spec=Device)
    peer2.id = "peer-2-id"
    peer2.name = "Peer Device 2"
    peer2.wireguard_ip = "10.0.0.4"
    peer2.public_key = "peer2_public_key_9876543210987654321098"
    peer2.enabled = True
    peer2.preshared_key_encrypted = None
    _apply_device_endpoints(peer2, "peer2.example.com:51820", None)
    peer2.location = location2  # Different location

    device.network.locations = [location1, location2]
    device.network.devices = [device, peer1, peer2]

    return device


class TestDeviceConfigService:
    """Test device configuration service."""

    @pytest.mark.asyncio
    async def test_generate_device_config_wg_format(
        self, device_config_service: DeviceConfigService, mock_device: Device
    ) -> None:
        """Test generating WireGuard configuration in wg format."""
        config_response = await device_config_service.generate_device_config(
            device=mock_device,
            device_private_key="test_private_key",
            format_type="wg",
        )

        assert isinstance(config_response, DeviceConfigResponse)
        assert config_response.device_id == mock_device.id
        assert config_response.device_name == mock_device.name
        assert config_response.network_name == mock_device.network.name
        assert config_response.format == "wg"

        # Check configuration content
        config_str = str(config_response.configuration)
        assert "[Interface]" in config_str
        assert "PrivateKey = test_private_key" in config_str
        assert "Address = 10.0.0.2/24" in config_str
        assert "DNS = 8.8.8.8,8.8.4.4" in config_str
        assert "MTU = 1420" in config_str

        # Check mesh topology peer configuration
        assert "[Peer]" in config_str
        # Should have peer device (not network public key)
        assert "PublicKey = peer1_public_key_1234567890123456789012" in config_str
        # Mesh topology uses /32 for each peer (not full network CIDR)
        assert "AllowedIPs = 10.0.0.3/32" in config_str
        # Uses peer's endpoint
        assert "Endpoint = peer1.example.com:51820" in config_str
        assert "PersistentKeepalive = 25" in config_str

    @pytest.mark.asyncio
    async def test_generate_device_config_with_peer_link_properties(
        self, device_config_service: DeviceConfigService, mock_device: Device
    ) -> None:
        """Ensure per-link properties override defaults."""
        link = MagicMock(spec=DevicePeerLink)
        link.from_device_id = mock_device.id
        link.to_device_id = "peer-1-id"
        link.properties = {"PersistentKeepalive": 10, "Description": "Backhaul"}
        link.preshared_key_encrypted = None
        link.preshared_key_encrypted_dek = None
        mock_device.network.device_peer_links = [link]

        config_response = await device_config_service.generate_device_config(
            device=mock_device,
            device_private_key="test_private_key",
            format_type="wg",
        )

        config_str = str(config_response.configuration)
        assert "PersistentKeepalive = 10" in config_str
        assert "Description = Backhaul" in config_str

    @pytest.mark.asyncio
    async def test_generate_device_config_with_listen_port(
        self, device_config_service: DeviceConfigService, mock_device: Device
    ) -> None:
        """Test that ListenPort is included in configuration when device has port."""
        # Set internal endpoint port
        _apply_device_endpoints(mock_device, None, "192.168.1.10:51820")

        config_response = await device_config_service.generate_device_config(
            device=mock_device,
            device_private_key="test_private_key",
            format_type="wg",
        )

        config_str = str(config_response.configuration)
        assert "ListenPort = 51820" in config_str

    @pytest.mark.asyncio
    async def test_generate_device_config_listen_port_prefer_internal(
        self, device_config_service: DeviceConfigService, mock_device: Device
    ) -> None:
        """Test that ListenPort prefers internal endpoint port over external."""
        # Set both internal and external ports (different values)
        _apply_device_endpoints(
            mock_device, "vpn.example.com:54321", "192.168.1.10:51820"
        )

        config_response = await device_config_service.generate_device_config(
            device=mock_device,
            device_private_key="test_private_key",
            format_type="wg",
        )

        config_str = str(config_response.configuration)
        # Should prefer internal port (51820) over external port (54321)
        assert "ListenPort = 51820" in config_str
        assert "ListenPort = 54321" not in config_str

    @pytest.mark.asyncio
    async def test_generate_device_config_listen_port_external_fallback(
        self, device_config_service: DeviceConfigService, mock_device: Device
    ) -> None:
        """Test that ListenPort falls back to external port when internal not set."""
        # Set only external port
        _apply_device_endpoints(mock_device, "vpn.example.com:12345", None)

        config_response = await device_config_service.generate_device_config(
            device=mock_device,
            device_private_key="test_private_key",
            format_type="wg",
        )

        config_str = str(config_response.configuration)
        assert "ListenPort = 12345" in config_str

    @pytest.mark.asyncio
    async def test_generate_device_config_no_listen_port_without_ports(
        self, device_config_service: DeviceConfigService, mock_device: Device
    ) -> None:
        """Test that ListenPort is not included when device has no ports."""
        # Ensure no ports are set
        _apply_device_endpoints(mock_device, None, None)

        config_response = await device_config_service.generate_device_config(
            device=mock_device,
            device_private_key="test_private_key",
            format_type="wg",
        )

        config_str = str(config_response.configuration)
        # Should not include ListenPort line
        assert "ListenPort =" not in config_str

    @pytest.mark.asyncio
    async def test_generate_device_config_listen_port_override(
        self, device_config_service: DeviceConfigService, mock_device: Device
    ) -> None:
        """Test that ListenPort can be overridden via interface_properties."""
        # Set internal port
        _apply_device_endpoints(mock_device, None, "192.168.1.10:51820")
        # Override ListenPort via interface_properties
        mock_device.interface_properties = {"ListenPort": 9999}

        config_response = await device_config_service.generate_device_config(
            device=mock_device,
            device_private_key="test_private_key",
            format_type="wg",
        )

        config_str = str(config_response.configuration)
        # Should use overridden port
        assert "ListenPort = 9999" in config_str
        assert "ListenPort = 51820" not in config_str

    @pytest.mark.asyncio
    async def test_generate_device_config_json_format(
        self, device_config_service: DeviceConfigService, mock_device: Device
    ) -> None:
        """Test generating WireGuard configuration in JSON format."""
        config_response = await device_config_service.generate_device_config(
            device=mock_device,
            device_private_key="test_private_key",
            format_type="json",
        )

        assert isinstance(config_response, DeviceConfigResponse)
        assert config_response.format == "json"

        # Check that configuration is a structured object
        config = config_response.configuration
        assert hasattr(config, "interface")
        assert hasattr(config, "peers")  # Changed from "peer" to "peers"
        assert config.interface.private_key == "test_private_key"
        assert config.interface.address == "10.0.0.2/24"

        # Check mesh topology peers list
        assert len(config.peers) == 1
        assert config.peers[0].public_key == "peer1_public_key_1234567890123456789012"
        assert config.peers[0].allowed_ips == "10.0.0.3/32"
        assert config.peers[0].endpoint == "peer1.example.com:51820"
        assert config.peers[0].persistent_keepalive == 25

    @pytest.mark.asyncio
    async def test_generate_device_config_mobile_format(
        self, device_config_service: DeviceConfigService, mock_device: Device
    ) -> None:
        """Test generating WireGuard configuration in mobile format."""
        config_response = await device_config_service.generate_device_config(
            device=mock_device,
            device_private_key="test_private_key",
            format_type="mobile",
            platform="ios",
        )

        assert isinstance(config_response, DeviceConfigResponse)
        assert config_response.format == "mobile"

        # Check mobile-specific configuration
        config = config_response.configuration
        assert hasattr(config, "name")
        assert hasattr(config, "addresses")
        assert hasattr(config, "dns")
        assert "ios".lower() in config.name.lower()
        assert "10.0.0.2/24" in config.addresses
        assert config.dns == ["8.8.8.8", "8.8.4.4"]

    @pytest.mark.asyncio
    async def test_generate_device_config_respects_network_prefix(
        self, device_config_service: DeviceConfigService, mock_device: Device
    ) -> None:
        """Ensure network prefix length is applied to interface address."""
        mock_device.network.network_cidr = "10.0.0.0/16"

        config_response = await device_config_service.generate_device_config(
            device=mock_device,
            device_private_key="test_private_key",
            format_type="wg",
        )

        config_str = str(config_response.configuration)
        assert "Address = 10.0.0.2/16" in config_str

    @pytest.mark.asyncio
    async def test_generate_device_config_small_prefix(
        self, device_config_service: DeviceConfigService, mock_device: Device
    ) -> None:
        """Support generation for narrow subnets."""
        mock_device.network.network_cidr = "10.0.0.0/28"
        mock_device.wireguard_ip = "10.0.0.2"

        config_response = await device_config_service.generate_device_config(
            device=mock_device,
            device_private_key="test_private_key",
            format_type="wg",
        )

        config_str = str(config_response.configuration)
        assert "Address = 10.0.0.2/28" in config_str

    @pytest.mark.asyncio
    async def test_generate_device_config_invalid_ip_raises(
        self, device_config_service: DeviceConfigService, mock_device: Device
    ) -> None:
        """Raise an error when device IP falls outside the network CIDR."""
        mock_device.network.network_cidr = "10.0.0.0/28"
        mock_device.wireguard_ip = "10.0.1.10"

        with pytest.raises(
            ValueError, match="Device IP 10.0.1.10 is not within network"
        ):
            await device_config_service.generate_device_config(
                device=mock_device,
                device_private_key="test_private_key",
                format_type="wg",
            )

    @pytest.mark.asyncio
    async def test_generate_device_config_fallback_endpoint(
        self,
        device_config_service: DeviceConfigService,
        mock_device_with_network_locations: Device,
        unlocked_master_password: str,
    ) -> None:
        """Test endpoint selection rules for mesh topology.

        Mesh topology rules:
        - Same location: use peer's internal endpoint
        - Different location: use peer's external endpoint
        """
        config_response = await device_config_service.generate_device_config(
            device=mock_device_with_network_locations,
            device_private_key="test_private_key",
            format_type="wg",
        )

        config_str = str(config_response.configuration)

        # Peer 1 is in same location - should use internal endpoint
        assert "Endpoint = 192.168.1.11:51820" in config_str
        # Peer 2 is in different location - should use external endpoint
        assert "Endpoint = peer2.example.com:51820" in config_str

    @pytest.mark.asyncio
    async def test_generate_device_config_no_endpoint(
        self, device_config_service: DeviceConfigService, mock_device: Device
    ) -> None:
        """Test configuration generation when peer has no endpoint available."""
        # Set up a peer with no endpoint
        _apply_device_endpoints(mock_device.network.devices[1], None, None)
        mock_device.network.devices[1].location = None

        config_response = await device_config_service.generate_device_config(
            device=mock_device,
            device_private_key="test_private_key",
            format_type="wg",
        )

        config_str = str(config_response.configuration)
        # Since peer has no endpoint, there should be no Endpoint line in output
        assert "Endpoint =" not in config_str

    @pytest.mark.asyncio
    async def test_external_endpoint_inherits_location_host(
        self, device_config_service: DeviceConfigService, mock_device: Device
    ) -> None:
        """Test that missing external host falls back to the location host."""
        peer = mock_device.network.devices[1]
        _apply_device_endpoints(peer, None, None)
        peer.external_endpoint_port = 51820
        peer.location.external_endpoint = "vpn.example.com"

        config_response = await device_config_service.generate_device_config(
            device=mock_device,
            device_private_key="test_private_key",
            format_type="wg",
        )

        config_str = str(config_response.configuration)
        assert "Endpoint = vpn.example.com:51820" in config_str

    @pytest.mark.asyncio
    async def test_generate_device_config_no_dns(
        self, device_config_service: DeviceConfigService, mock_device: Device
    ) -> None:
        """Test configuration generation when no DNS is configured."""
        mock_device.network.dns_servers = None

        config_response = await device_config_service.generate_device_config(
            device=mock_device,
            device_private_key="test_private_key",
            format_type="wg",
        )

        config_str = str(config_response.configuration)
        # Should not include DNS line
        assert "DNS =" not in config_str

    @pytest.mark.asyncio
    async def test_generate_device_config_no_mtu(
        self, device_config_service: DeviceConfigService, mock_device: Device
    ) -> None:
        """Test configuration generation when no MTU is configured."""
        mock_device.network.mtu = None

        config_response = await device_config_service.generate_device_config(
            device=mock_device,
            device_private_key="test_private_key",
            format_type="wg",
        )

        config_str = str(config_response.configuration)
        # Should not include MTU line
        assert "MTU =" not in config_str

    @pytest.mark.asyncio
    async def test_generate_device_config_mtu_override_via_properties(
        self,
        device_config_service: DeviceConfigService,
        mock_device: Device,
    ) -> None:
        """Test device-level MTU override via interface_properties."""
        # Set network MTU to 1420
        mock_device.network.mtu = 1420
        # Override with device-level MTU via interface_properties
        mock_device.interface_properties = {"MTU": 1280}

        config_response = await device_config_service.generate_device_config(
            device=mock_device,
            device_private_key="test_private_key",
            format_type="wg",
        )

        config_str = str(config_response.configuration)
        # Should include device-level MTU, not network MTU
        assert "MTU = 1280" in config_str
        assert "MTU = 1420" not in config_str

    @pytest.mark.asyncio
    async def test_generate_device_config_mtu_string_value(
        self,
        device_config_service: DeviceConfigService,
        mock_device: Device,
    ) -> None:
        """Test that string MTU values are converted to integers."""
        # Set network MTU to 1420
        mock_device.network.mtu = 1420
        # Override with string MTU via interface_properties
        mock_device.interface_properties = {"MTU": "1280"}

        config_response = await device_config_service.generate_device_config(
            device=mock_device,
            device_private_key="test_private_key",
            format_type="wg",
        )

        config_str = str(config_response.configuration)
        # Should convert string to integer and use device-level MTU
        assert "MTU = 1280" in config_str
        assert "MTU = 1420" not in config_str

    @pytest.mark.asyncio
    async def test_generate_device_config_mtu_empty_string(
        self,
        device_config_service: DeviceConfigService,
        mock_device: Device,
    ) -> None:
        """Test that empty string MTU falls back to network MTU."""
        # Set network MTU to 1420
        mock_device.network.mtu = 1420
        # Set empty string MTU via interface_properties
        mock_device.interface_properties = {"MTU": ""}

        config_response = await device_config_service.generate_device_config(
            device=mock_device,
            device_private_key="test_private_key",
            format_type="wg",
        )

        config_str = str(config_response.configuration)
        # Should fall back to network MTU
        assert "MTU = 1420" in config_str

    @pytest.mark.asyncio
    async def test_generate_device_config_mtu_invalid_string(
        self,
        device_config_service: DeviceConfigService,
        mock_device: Device,
    ) -> None:
        """Test that invalid string MTU falls back to network MTU."""
        # Set network MTU to 1420
        mock_device.network.mtu = 1420
        # Set invalid string MTU via interface_properties
        mock_device.interface_properties = {"MTU": "invalid"}

        config_response = await device_config_service.generate_device_config(
            device=mock_device,
            device_private_key="test_private_key",
            format_type="wg",
        )

        config_str = str(config_response.configuration)
        # Should fall back to network MTU
        assert "MTU = 1420" in config_str

    @pytest.mark.asyncio
    async def test_generate_device_config_with_preshared_key(
        self,
        device_config_service: DeviceConfigService,
        mock_device: Device,
        unlocked_master_password: str,
    ) -> None:
        """Test configuration generation with preshared key."""
        mock_device.preshared_key_encrypted = encrypt_preshared_key(
            "F6rQePdvfo7+/CezvO2dTku5wh8pVufCB2i4yhtEiS0=",  # pragma: allowlist secret
            unlocked_master_password,
        )

        config_response = await device_config_service.generate_device_config(
            device=mock_device,
            device_private_key="test_private_key",
            format_type="wg",
        )

        config_str = str(config_response.configuration)
        # Should include decrypted PresharedKey line
        assert (
            "PresharedKey = F6rQePdvfo7+/CezvO2dTku5wh8pVufCB2i4yhtEiS0="
            in config_str  # pragma: allowlist secret
        )

    @pytest.mark.asyncio
    async def test_generate_device_config_with_peer_link_preshared_key(
        self,
        device_config_service: DeviceConfigService,
        mock_device: Device,
        unlocked_master_password: str,
    ) -> None:
        """Test per-peer preshared key takes precedence."""
        peer_psk = "cHgtbE1hZ2ljUGVlcjEyMzQ1Njc4OTAxMjM0NTY3ODk="  # pragma: allowlist secret
        link = MagicMock(spec=DevicePeerLink)
        link.from_device_id = mock_device.id
        link.to_device_id = "peer-1-id"
        link.properties = {}
        link.preshared_key_encrypted = encrypt_preshared_key(
            peer_psk, unlocked_master_password
        )
        link.preshared_key_encrypted_dek = None
        mock_device.network.device_peer_links = [link]

        config_response = await device_config_service.generate_device_config(
            device=mock_device,
            device_private_key="test_private_key",
            format_type="wg",
        )

        config_str = str(config_response.configuration)
        assert f"PresharedKey = {peer_psk}" in config_str

    @pytest.mark.asyncio
    async def test_generate_device_config_network_preshared_key(
        self,
        device_config_service: DeviceConfigService,
        mock_device: Device,
        unlocked_master_password: str,
    ) -> None:
        """Test configuration uses network preshared key when device PSK missing."""
        mock_device.preshared_key_encrypted = None
        mock_device.location.preshared_key_encrypted = None
        mock_device.network.preshared_key_encrypted = encrypt_preshared_key(
            "b0w7ipX1SXZ/dwOqP9iSQxydgFDIt/O7L4vz2hJW54E=",  # pragma: allowlist secret
            unlocked_master_password,
        )

        config_response = await device_config_service.generate_device_config(
            device=mock_device,
            device_private_key="test_private_key",
            format_type="wg",
        )

        config_str = str(config_response.configuration)
        assert (
            "PresharedKey = b0w7ipX1SXZ/dwOqP9iSQxydgFDIt/O7L4vz2hJW54E="
            in config_str  # pragma: allowlist secret
        )

    @pytest.mark.asyncio
    async def test_generate_device_config_location_preshared_key(
        self,
        device_config_service: DeviceConfigService,
        mock_device: Device,
        unlocked_master_password: str,
    ) -> None:
        """Test configuration uses location preshared key when device PSK missing."""
        mock_device.preshared_key_encrypted = None
        mock_device.network.preshared_key_encrypted = encrypt_preshared_key(
            "b0w7ipX1SXZ/dwOqP9iSQxydgFDIt/O7L4vz2hJW54E=",  # pragma: allowlist secret
            unlocked_master_password,
        )
        mock_device.location.preshared_key_encrypted = encrypt_preshared_key(
            "1d5yfn6m1s8dVBC45p4Vw6F1G38lQ0RrgvG9nVxYz8E=",  # pragma: allowlist secret
            unlocked_master_password,
        )

        config_response = await device_config_service.generate_device_config(
            device=mock_device,
            device_private_key="test_private_key",
            format_type="wg",
        )

        config_str = str(config_response.configuration)
        assert (
            "PresharedKey = 1d5yfn6m1s8dVBC45p4Vw6F1G38lQ0RrgvG9nVxYz8E="
            in config_str  # pragma: allowlist secret
        )
