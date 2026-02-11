"""Tests for validating mesh topology configuration generation with multiple devices.

This test file focuses on validating that mesh topology works correctly with
larger numbers of devices, complex topologies, and edge cases.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.schemas.device_config import DeviceConfiguration
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


def _create_mock_network(
    name: str = "Test Network",
    cidr: str = "10.0.0.0/24",
    preshared_key: str | None = None,
    password: str | None = None,
) -> MagicMock:
    """Create a mock network for testing."""
    network = MagicMock()
    network.name = name
    network.network_cidr = cidr
    network.public_key = "test_network_public_key"
    network.dns_servers = None
    network.mtu = None
    network.persistent_keepalive = None
    network.preshared_key_encrypted = (
        encrypt_preshared_key(preshared_key, password)
        if preshared_key and password
        else None
    )
    network.locations = []
    network.devices = []
    return network


def _create_mock_location(
    location_id: str,
    name: str,
    external_endpoint: str,
    internal_endpoint: str | None = None,
) -> MagicMock:
    """Create a mock location for testing."""
    location = MagicMock()
    location.id = location_id
    location.name = name
    location.external_endpoint = external_endpoint
    location.internal_endpoint = internal_endpoint
    location.preshared_key_encrypted = None
    return location


def _create_mock_device(
    device_id: str,
    name: str,
    wireguard_ip: str,
    public_key: str,
    location: MagicMock,
    enabled: bool = True,
    external_endpoint: str | None = None,
    internal_endpoint: str | None = None,
) -> MagicMock:
    """Create a mock device for testing."""
    device = MagicMock()
    device.id = device_id
    device.name = name
    device.wireguard_ip = wireguard_ip
    device.public_key = public_key
    device.enabled = enabled
    device.preshared_key_encrypted = None
    device.location_preshared_key_encrypted = None
    device.external_endpoint = external_endpoint
    device.internal_endpoint = internal_endpoint
    device.external_endpoint_host, device.external_endpoint_port = _split_endpoint(
        external_endpoint
    )
    device.internal_endpoint_host, device.internal_endpoint_port = _split_endpoint(
        internal_endpoint
    )
    device.location = location
    return device


class TestMeshTopologyValidation:
    """Test mesh topology with multiple devices."""

    @pytest.fixture
    def device_config_service(self) -> DeviceConfigService:
        """Create a device config service with a mock database."""
        mock_db = MagicMock()
        return DeviceConfigService(mock_db)

    @pytest.fixture
    def large_mesh_network(self) -> MagicMock:
        """Create a network with 7 devices across 3 locations for comprehensive mesh testing."""
        network = _create_mock_network(
            name="Large Mesh Network",
            cidr="10.0.0.0/24",
        )

        # Create 3 locations
        location1 = _create_mock_location(
            location_id="loc-1",
            name="Data Center East",
            external_endpoint="vpn-east.example.com:51820",
            internal_endpoint="10.1.1.1:51820",
        )
        location2 = _create_mock_location(
            location_id="loc-2",
            name="Data Center West",
            external_endpoint="vpn-west.example.com:51820",
            internal_endpoint="10.2.1.1:51820",
        )
        location3 = _create_mock_location(
            location_id="loc-3",
            name="Cloud Region",
            external_endpoint="vpn-cloud.example.com:51820",
            internal_endpoint="10.3.1.1:51820",
        )
        network.locations = [location1, location2, location3]

        # Create 7 devices distributed across locations
        devices = [
            _create_mock_device(
                device_id="dev-1",
                name="Server-1-East",
                wireguard_ip="10.0.0.2",
                public_key="key1_ABCDEF1234567890123456789012345678",
                location=location1,
                external_endpoint="10.1.1.10:51820",
                internal_endpoint="10.1.1.10:51820",
            ),
            _create_mock_device(
                device_id="dev-2",
                name="Server-2-East",
                wireguard_ip="10.0.0.3",
                public_key="key2_ABCDEF1234567890123456789012345678",
                location=location1,
                external_endpoint="10.1.1.11:51820",
                internal_endpoint="10.1.1.11:51820",
            ),
            _create_mock_device(
                device_id="dev-3",
                name="Server-3-East",
                wireguard_ip="10.0.0.4",
                public_key="key3_ABCDEF1234567890123456789012345678",
                location=location1,
                external_endpoint="10.1.1.12:51820",
                internal_endpoint="10.1.1.12:51820",
            ),
            _create_mock_device(
                device_id="dev-4",
                name="Server-1-West",
                wireguard_ip="10.0.0.5",
                public_key="key4_ABCDEF1234567890123456789012345678",
                location=location2,
                external_endpoint="10.2.1.10:51820",
                internal_endpoint="10.2.1.10:51820",
            ),
            _create_mock_device(
                device_id="dev-5",
                name="Server-2-West",
                wireguard_ip="10.0.0.6",
                public_key="key5_ABCDEF1234567890123456789012345678",
                location=location2,
                external_endpoint="10.2.1.11:51820",
                internal_endpoint="10.2.1.11:51820",
            ),
            _create_mock_device(
                device_id="dev-6",
                name="Cloud-Node-1",
                wireguard_ip="10.0.0.7",
                public_key="key6_ABCDEF1234567890123456789012345678",
                location=location3,
                external_endpoint="10.3.1.10:51820",
                internal_endpoint="10.3.1.10:51820",
            ),
            _create_mock_device(
                device_id="dev-7",
                name="Cloud-Node-2",
                wireguard_ip="10.0.0.8",
                public_key="key7_ABCDEF1234567890123456789012345678",
                location=location3,
                external_endpoint="10.3.1.11:51820",
                internal_endpoint="10.3.1.11:51820",
            ),
        ]
        network.devices = devices

        # Set network reference for each device
        for device in devices:
            device.network = network

        return network

    @pytest.mark.asyncio
    async def test_large_mesh_config_generates_correct_peer_count(
        self,
        device_config_service: DeviceConfigService,
        large_mesh_network: MagicMock,
    ) -> None:
        """Test that each device in a 7-node mesh has 6 peers configured."""
        for device in large_mesh_network.devices:
            config = await device_config_service.generate_device_config(
                device=device,
                device_private_key="test_private_key",  # pragma: allowlist secret
                format_type="json",
            )

            # Type guard: format_type="json" returns DeviceConfiguration
            assert isinstance(config.configuration, DeviceConfiguration)

            # Check that we have 6 peers (all other devices except self)
            assert len(config.configuration.peers) == 6, (
                f"Device {device.name} should have 6 peers, "
                f"but got {len(config.configuration.peers)}"
            )

            # Verify peer IPs are unique and not the device's own IP
            peer_ips = {peer.allowed_ips for peer in config.configuration.peers}
            assert len(peer_ips) == 6, "Peer IPs should be unique"
            assert (
                f"{device.wireguard_ip}/32" not in peer_ips
            ), "Device should not be its own peer"

    @pytest.mark.asyncio
    async def test_mesh_endpoint_selection_rules(
        self,
        device_config_service: DeviceConfigService,
        large_mesh_network: MagicMock,
    ) -> None:
        """Test endpoint selection follows mesh topology rules:
        - Same location: use internal endpoint
        - Different location: use external endpoint
        """
        # Test a device in location 1 (Data Center East)
        device_east = large_mesh_network.devices[0]  # dev-1 in loc-1

        config = await device_config_service.generate_device_config(
            device=device_east,
            device_private_key="test_private_key",  # pragma: allowlist secret
            format_type="json",
        )

        assert isinstance(config.configuration, DeviceConfiguration)

        # Find peers and their endpoints
        peer_endpoints = {
            peer.allowed_ips: peer.endpoint for peer in config.configuration.peers
        }

        # Peers in same location (East) should use internal endpoints
        assert (
            peer_endpoints["10.0.0.3/32"] == "10.1.1.11:51820"
        ), "Peer in same location should use internal endpoint"
        assert (
            peer_endpoints["10.0.0.4/32"] == "10.1.1.12:51820"
        ), "Peer in same location should use internal endpoint"

        # Peers in different locations (West/Cloud) should use external endpoints
        assert (
            peer_endpoints["10.0.0.5/32"] == "10.2.1.10:51820"
        ), "Peer in different location should use external endpoint"
        assert (
            peer_endpoints["10.0.0.6/32"] == "10.2.1.11:51820"
        ), "Peer in different location should use external endpoint"
        assert (
            peer_endpoints["10.0.0.7/32"] == "10.3.1.10:51820"
        ), "Peer in different location should use external endpoint"
        assert (
            peer_endpoints["10.0.0.8/32"] == "10.3.1.11:51820"
        ), "Peer in different location should use external endpoint"

    @pytest.mark.asyncio
    async def test_mesh_bidirectional_connectivity(
        self,
        device_config_service: DeviceConfigService,
        large_mesh_network: MagicMock,
    ) -> None:
        """Test that bidirectional connectivity is maintained across the mesh.

        If device A has device B as a peer, then device B should also have device A as a peer.
        """
        configs = {}
        for device in large_mesh_network.devices:
            config = await device_config_service.generate_device_config(
                device=device,
                device_private_key="test_private_key",  # pragma: allowlist secret
                format_type="json",
            )
            assert isinstance(config.configuration, DeviceConfiguration)
            configs[device.id] = {
                "device": device,
                "peers": {
                    peer.allowed_ips: peer for peer in config.configuration.peers
                },
            }

        # Check bidirectional connectivity for all pairs
        for dev1_id, dev1_info in configs.items():
            for dev2_id, dev2_info in configs.items():
                if dev1_id == dev2_id:
                    continue

                dev1 = dev1_info["device"]
                dev2 = dev2_info["device"]

                # dev1 should have dev2 as a peer
                dev1_has_dev2 = f"{dev2.wireguard_ip}/32" in dev1_info["peers"]

                # dev2 should have dev1 as a peer
                dev2_has_dev1 = f"{dev1.wireguard_ip}/32" in dev2_info["peers"]

                assert dev1_has_dev2, f"{dev1.name} should have {dev2.name} as a peer"
                assert dev2_has_dev1, f"{dev2.name} should have {dev1.name} as a peer"

                # Verify endpoints are consistent
                if dev1_has_dev2 and dev2_has_dev1:
                    dev1_to_dev2_endpoint = dev1_info["peers"][
                        f"{dev2.wireguard_ip}/32"
                    ].endpoint
                    dev2_to_dev1_endpoint = dev2_info["peers"][
                        f"{dev1.wireguard_ip}/32"
                    ].endpoint

                    # Endpoints should be appropriate for each peer's perspective
                    # (internal for same location, external for different locations)
                    same_location = (
                        dev1.location
                        and dev2.location
                        and dev1.location.id == dev2.location.id
                    )
                    if same_location:
                        # Both should use internal endpoints
                        assert dev1_to_dev2_endpoint is not None
                        assert dev2_to_dev1_endpoint is not None

    @pytest.mark.asyncio
    async def test_mesh_all_devices_in_single_location(
        self,
        device_config_service: DeviceConfigService,
    ) -> None:
        """Test mesh topology when all devices are in a single location."""
        network = _create_mock_network(name="Single Location Mesh")

        location = _create_mock_location(
            location_id="loc-1",
            name="Single Location",
            external_endpoint="vpn.example.com:51820",
            internal_endpoint="10.1.1.1:51820",
        )
        network.locations = [location]

        # Create 5 devices all in the same location
        devices = [
            _create_mock_device(
                device_id=f"dev-{i}",
                name=f"Device-{i}",
                wireguard_ip=f"10.0.0.{i+2}",
                public_key=f"key{i}_ABCDEF1234567890123456789012345678",
                location=location,
                external_endpoint=f"10.1.1.{i+10}:51820",
                internal_endpoint=f"10.1.1.{i+10}:51820",
            )
            for i in range(5)
        ]
        network.devices = devices
        for device in devices:
            device.network = network

        # Test each device's configuration
        for device in devices:
            config = await device_config_service.generate_device_config(
                device=device,
                device_private_key="test_private_key",  # pragma: allowlist secret
                format_type="json",
            )

            assert isinstance(config.configuration, DeviceConfiguration)

            # Should have 4 peers (all other devices)
            assert len(config.configuration.peers) == 4

            # All peers should use internal endpoints (same location)
            for peer in config.configuration.peers:
                assert peer.endpoint is not None, "Peer should have an endpoint"
                assert peer.endpoint.startswith(
                    "10.1.1."
                ), "Peer should use internal endpoint for same location"

    @pytest.mark.asyncio
    async def test_mesh_all_devices_in_different_locations(
        self,
        device_config_service: DeviceConfigService,
    ) -> None:
        """Test mesh topology when each device is in a different location."""
        network = _create_mock_network(name="Distributed Location Mesh")

        # Create 5 devices, each in its own location
        devices = []
        for i in range(5):
            location = _create_mock_location(
                location_id=f"loc-{i}",
                name=f"Location-{i}",
                external_endpoint=f"vpn{i}.example.com:51820",
                internal_endpoint=f"10.{i}.1.1:51820",
            )
            network.locations.append(location)

            # Device external endpoints use public IP addresses
            # The device's external_endpoint is used when peers are in different locations
            device = _create_mock_device(
                device_id=f"dev-{i}",
                name=f"Device-{i}",
                wireguard_ip=f"10.0.0.{i+2}",
                public_key=f"key{i}_ABCDEF1234567890123456789012345678",
                location=location,
                external_endpoint=f"203.0.113.{i+10}:51820",
                internal_endpoint=f"10.{i}.1.10:51820",
            )
            device.network = network
            devices.append(device)

        network.devices = devices

        # Test each device's configuration
        for device in devices:
            config = await device_config_service.generate_device_config(
                device=device,
                device_private_key="test_private_key",  # pragma: allowlist secret
                format_type="json",
            )

            assert isinstance(config.configuration, DeviceConfiguration)

            # Should have 4 peers (all other devices)
            assert len(config.configuration.peers) == 4

            # All peers should use external endpoints (different locations)
            # The peer device's external_endpoint is used
            for peer in config.configuration.peers:
                assert peer.endpoint is not None, "Peer should have an endpoint"
                assert peer.endpoint.startswith(
                    "203.0.113."
                ), "Peer should use external endpoint for different location"

    @pytest.mark.asyncio
    async def test_mesh_mixed_topology(
        self,
        device_config_service: DeviceConfigService,
    ) -> None:
        """Test mesh topology with mixed scenario:
        - Some devices share a location
        - Some devices have unique locations
        """
        network = _create_mock_network(name="Mixed Topology Mesh")

        # Location 1 with 3 devices
        location1 = _create_mock_location(
            location_id="loc-1",
            name="Main Office",
            external_endpoint="vpn-main.example.com:51820",
            internal_endpoint="10.1.1.1:51820",
        )
        network.locations.append(location1)

        # Location 2 with 1 device
        location2 = _create_mock_location(
            location_id="loc-2",
            name="Branch Office",
            external_endpoint="vpn-branch.example.com:51820",
            internal_endpoint="10.2.1.1:51820",
        )
        network.locations.append(location2)

        # Location 3 with 1 device
        location3 = _create_mock_location(
            location_id="loc-3",
            name="Remote Site",
            external_endpoint="vpn-remote.example.com:51820",
            internal_endpoint="10.3.1.1:51820",
        )
        network.locations.append(location3)

        # Create devices
        devices = [
            # 3 devices in location 1
            _create_mock_device(
                device_id="dev-1",
                name="Main-Server-1",
                wireguard_ip="10.0.0.2",
                public_key="key1_ABCDEF1234567890123456789012345678",
                location=location1,
                external_endpoint="10.1.1.10:51820",
                internal_endpoint="10.1.1.10:51820",
            ),
            _create_mock_device(
                device_id="dev-2",
                name="Main-Server-2",
                wireguard_ip="10.0.0.3",
                public_key="key2_ABCDEF1234567890123456789012345678",
                location=location1,
                external_endpoint="10.1.1.11:51820",
                internal_endpoint="10.1.1.11:51820",
            ),
            _create_mock_device(
                device_id="dev-3",
                name="Main-Server-3",
                wireguard_ip="10.0.0.4",
                public_key="key3_ABCDEF1234567890123456789012345678",
                location=location1,
                external_endpoint="10.1.1.12:51820",
                internal_endpoint="10.1.1.12:51820",
            ),
            # 1 device in location 2
            _create_mock_device(
                device_id="dev-4",
                name="Branch-Gateway",
                wireguard_ip="10.0.0.5",
                public_key="key4_ABCDEF1234567890123456789012345678",
                location=location2,
                external_endpoint="10.2.1.10:51820",
                internal_endpoint="10.2.1.10:51820",
            ),
            # 1 device in location 3
            _create_mock_device(
                device_id="dev-5",
                name="Remote-Gateway",
                wireguard_ip="10.0.0.6",
                public_key="key5_ABCDEF1234567890123456789012345678",
                location=location3,
                external_endpoint="10.3.1.10:51820",
                internal_endpoint="10.3.1.10:51820",
            ),
        ]
        network.devices = devices
        for device in devices:
            device.network = network

        # Test a device in location 1 (has 2 peers in same location, 2 in different locations)
        device_main = devices[0]
        config_main = await device_config_service.generate_device_config(
            device=device_main,
            device_private_key="test_private_key",  # pragma: allowlist secret
            format_type="json",
        )

        assert isinstance(config_main.configuration, DeviceConfiguration)

        # Should have 4 peers total
        assert len(config_main.configuration.peers) == 4

        # Count peers using internal vs external endpoints
        internal_count = sum(
            1
            for p in config_main.configuration.peers
            if p.endpoint and p.endpoint.startswith("10.1.1.")
        )
        external_count = sum(
            1
            for p in config_main.configuration.peers
            if p.endpoint and not p.endpoint.startswith("10.1.1.")
        )

        # Should have 2 internal (same location) and 2 external (different locations)
        assert internal_count == 2, "Should have 2 peers in same location"
        assert external_count == 2, "Should have 2 peers in different locations"

        # Test a device in location 2 (all peers in different locations)
        device_branch = devices[3]
        config_branch = await device_config_service.generate_device_config(
            device=device_branch,
            device_private_key="test_private_key",  # pragma: allowlist secret
            format_type="json",
        )

        assert isinstance(config_branch.configuration, DeviceConfiguration)

        # Should have 4 peers total
        assert len(config_branch.configuration.peers) == 4

        # All peers should use external endpoints
        for peer in config_branch.configuration.peers:
            assert peer.endpoint is not None
            assert peer.endpoint.startswith("10.") and not peer.endpoint.startswith(
                "10.2."
            ), "All peers should be in different locations"

    @pytest.mark.asyncio
    async def test_mesh_with_disabled_devices(
        self,
        device_config_service: DeviceConfigService,
    ) -> None:
        """Test that disabled devices are excluded from mesh peer configurations."""
        network = _create_mock_network(name="Mesh with Disabled Devices")

        location = _create_mock_location(
            location_id="loc-1",
            name="Main Location",
            external_endpoint="vpn.example.com:51820",
            internal_endpoint="10.1.1.1:51820",
        )
        network.locations = [location]

        # Create devices, some enabled, some disabled
        devices = [
            _create_mock_device(
                device_id="dev-1",
                name="Enabled-1",
                wireguard_ip="10.0.0.2",
                public_key="key1_ABCDEF1234567890123456789012345678",
                location=location,
                enabled=True,
                external_endpoint="10.1.1.10:51820",
                internal_endpoint="10.1.1.10:51820",
            ),
            _create_mock_device(
                device_id="dev-2",
                name="Enabled-2",
                wireguard_ip="10.0.0.3",
                public_key="key2_ABCDEF1234567890123456789012345678",
                location=location,
                enabled=True,
                external_endpoint="10.1.1.11:51820",
                internal_endpoint="10.1.1.11:51820",
            ),
            _create_mock_device(
                device_id="dev-3",
                name="Disabled-1",
                wireguard_ip="10.0.0.4",
                public_key="key3_ABCDEF1234567890123456789012345678",
                location=location,
                enabled=False,
                external_endpoint="10.1.1.12:51820",
                internal_endpoint="10.1.1.12:51820",
            ),
            _create_mock_device(
                device_id="dev-4",
                name="Enabled-3",
                wireguard_ip="10.0.0.5",
                public_key="key4_ABCDEF1234567890123456789012345678",
                location=location,
                enabled=True,
                external_endpoint="10.1.1.13:51820",
                internal_endpoint="10.1.1.13:51820",
            ),
        ]
        network.devices = devices
        for device in devices:
            device.network = network

        # Test an enabled device - should only see other enabled devices as peers
        enabled_device = devices[0]
        config = await device_config_service.generate_device_config(
            device=enabled_device,
            device_private_key="test_private_key",  # pragma: allowlist secret
            format_type="json",
        )

        assert isinstance(config.configuration, DeviceConfiguration)

        # Should have 2 peers (the other two enabled devices, not the disabled one)
        assert len(config.configuration.peers) == 2

        # Verify disabled device is not in the peer list
        peer_public_keys = {peer.public_key for peer in config.configuration.peers}
        assert (
            "key3_ABCDEF1234567890123456789012345678" not in peer_public_keys
        ), "Disabled device should not be a peer"

    @pytest.mark.asyncio
    async def test_mesh_devices_without_endpoints(
        self,
        device_config_service: DeviceConfigService,
    ) -> None:
        """Test mesh topology when some devices have no configured endpoints."""
        network = _create_mock_network(name="Mesh with Missing Endpoints")

        location = _create_mock_location(
            location_id="loc-1",
            name="Main Location",
            external_endpoint="vpn.example.com:51820",
            internal_endpoint="10.1.1.1:51820",
        )
        network.locations = [location]

        devices = [
            _create_mock_device(
                device_id="dev-1",
                name="Device-With-Endpoint",
                wireguard_ip="10.0.0.2",
                public_key="key1_ABCDEF1234567890123456789012345678",
                location=location,
                external_endpoint="10.1.1.10:51820",
                internal_endpoint="10.1.1.10:51820",
            ),
            _create_mock_device(
                device_id="dev-2",
                name="Device-No-Endpoint",
                wireguard_ip="10.0.0.3",
                public_key="key2_ABCDEF1234567890123456789012345678",
                location=location,
                external_endpoint=None,
                internal_endpoint=None,
            ),
        ]
        network.devices = devices
        for device in devices:
            device.network = network

        # Test device with endpoint - should still include the device without endpoint
        config = await device_config_service.generate_device_config(
            device=devices[0],
            device_private_key="test_private_key",  # pragma: allowlist secret
            format_type="json",
        )

        assert isinstance(config.configuration, DeviceConfiguration)

        # Should have 1 peer (the device without endpoint should still be included)
        assert len(config.configuration.peers) == 1

        # The peer without endpoint should fall back to location internal endpoint
        assert (
            config.configuration.peers[0].endpoint == "10.1.1.1:51820"
        ), "Peer without configured endpoint should use location internal endpoint"

    @pytest.mark.asyncio
    async def test_mesh_deterministic_peer_ordering(
        self,
        device_config_service: DeviceConfigService,
        large_mesh_network: MagicMock,
    ) -> None:
        """Test that peer ordering is deterministic across multiple generations."""
        device = large_mesh_network.devices[0]

        # Generate config twice
        config1 = await device_config_service.generate_device_config(
            device=device,
            device_private_key="test_private_key",  # pragma: allowlist secret
            format_type="json",
        )
        config2 = await device_config_service.generate_device_config(
            device=device,
            device_private_key="test_private_key",  # pragma: allowlist secret
            format_type="json",
        )

        assert isinstance(config1.configuration, DeviceConfiguration)
        assert isinstance(config2.configuration, DeviceConfiguration)

        # Peers should be in the same order
        peers1 = [p.allowed_ips for p in config1.configuration.peers]
        peers2 = [p.allowed_ips for p in config2.configuration.peers]

        assert peers1 == peers2, "Peer ordering should be deterministic"

        # Peers should be ordered by IP address
        assert peers1 == sorted(peers1), "Peers should be ordered by IP address"

    @pytest.mark.asyncio
    async def test_mesh_wg_format_with_multiple_peers(
        self,
        device_config_service: DeviceConfigService,
        large_mesh_network: MagicMock,
    ) -> None:
        """Test that wg format generates correct multiple peer sections."""
        device = large_mesh_network.devices[0]

        config = await device_config_service.generate_device_config(
            device=device,
            device_private_key="test_private_key",  # pragma: allowlist secret
            format_type="wg",
        )

        config_str = str(config.configuration)

        # Count [Peer] sections - should have 6 peers
        peer_count = config_str.count("[Peer]")
        assert peer_count == 6, f"Should have 6 [Peer] sections, got {peer_count}"

        # Verify each peer section has required fields
        for peer in large_mesh_network.devices:
            if peer.id == device.id:
                continue
            assert (
                f"PublicKey = {peer.public_key}" in config_str
            ), f"Peer {peer.name} should have PublicKey"
            assert (
                f"AllowedIPs = {peer.wireguard_ip}/32" in config_str
            ), f"Peer {peer.name} should have correct AllowedIPs"

        # Verify interface section
        assert "[Interface]" in config_str
        assert "PrivateKey = test_private_key" in config_str
        assert f"Address = {device.wireguard_ip}/24" in config_str

    @pytest.mark.asyncio
    async def test_mesh_with_network_preshared_key(
        self,
        device_config_service: DeviceConfigService,
        unlocked_master_password: str,
    ) -> None:
        """Test that network preshared key is applied to all peers in mesh."""
        # Valid 32-byte base64 encoded preshared key
        network_psk = (
            "b0w7ipX1SXZ/dwOqP9iSQxydgFDIt/O7L4vz2hJW54E="  # pragma: allowlist secret
        )

        network = _create_mock_network(
            name="Mesh with PSK",
            cidr="10.0.0.0/24",
            preshared_key=network_psk,
            password=unlocked_master_password,
        )

        location = _create_mock_location(
            location_id="loc-1",
            name="Main Location",
            external_endpoint="vpn.example.com:51820",
            internal_endpoint="10.1.1.1:51820",
        )
        network.locations = [location]

        devices = [
            _create_mock_device(
                device_id=f"dev-{i}",
                name=f"Device-{i}",
                wireguard_ip=f"10.0.0.{i+2}",
                public_key=f"key{i}_ABCDEF1234567890123456789012345678",
                location=location,
                external_endpoint=f"10.1.1.{i+10}:51820",
                internal_endpoint=f"10.1.1.{i+10}:51820",
            )
            for i in range(3)
        ]
        network.devices = devices
        for device in devices:
            device.network = network

        # Test each device's configuration
        for device in devices:
            config = await device_config_service.generate_device_config(
                device=device,
                device_private_key="test_private_key",  # pragma: allowlist secret
                format_type="wg",
            )

            config_str = str(config.configuration)

            # Each peer should have the network PSK
            peer_count = config_str.count("[Peer]")
            psk_count = config_str.count("PresharedKey")

            assert peer_count == 2, f"Should have 2 peers, got {peer_count}"
            assert (
                psk_count == 2
            ), f"Should have 2 PresharedKey entries, got {psk_count}"
            assert (
                f"PresharedKey = {network_psk}" in config_str
            ), "Should have network PSK"

    @pytest.mark.asyncio
    async def test_mesh_with_all_network_options(
        self,
        device_config_service: DeviceConfigService,
    ) -> None:
        """Test mesh configuration with all network options (DNS, MTU, Keepalive)."""
        network = _create_mock_network(name="Full Options Mesh")
        network.dns_servers = "8.8.8.8,8.8.4.4"
        network.mtu = 1420
        network.persistent_keepalive = 25

        location = _create_mock_location(
            location_id="loc-1",
            name="Main Location",
            external_endpoint="vpn.example.com:51820",
            internal_endpoint="10.1.1.1:51820",
        )
        network.locations = [location]

        devices = [
            _create_mock_device(
                device_id=f"dev-{i}",
                name=f"Device-{i}",
                wireguard_ip=f"10.0.0.{i+2}",
                public_key=f"key{i}_ABCDEF1234567890123456789012345678",
                location=location,
                external_endpoint=f"10.1.1.{i+10}:51820",
                internal_endpoint=f"10.1.1.{i+10}:51820",
            )
            for i in range(3)
        ]
        network.devices = devices
        for device in devices:
            device.network = network

        config = await device_config_service.generate_device_config(
            device=devices[0],
            device_private_key="test_private_key",  # pragma: allowlist secret
            format_type="wg",
        )

        config_str = str(config.configuration)

        # Verify all interface options are present
        assert "DNS = 8.8.8.8,8.8.4.4" in config_str
        assert "MTU = 1420" in config_str
        assert "PersistentKeepalive = 25" in config_str
