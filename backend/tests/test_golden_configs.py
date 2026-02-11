"""Golden-file tests for device configuration generation."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.services.device_config import DeviceConfigService
from app.utils.key_management import encrypt_preshared_key

pytestmark = pytest.mark.usefixtures("unlocked_master_password")


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


def _create_test_device(
    wireguard_ip: str = "10.0.0.2",
    location_id: str = "location-1",
    location_name: str = "Location 1",
    external_endpoint: str = "vpn.example.com:51820",
    internal_endpoint: str | None = None,
) -> MagicMock:
    device = MagicMock()
    device.id = "test-device-id"
    device.name = "Test Device"
    device.wireguard_ip = wireguard_ip
    device.preshared_key_encrypted = None
    device.location_preshared_key_encrypted = None

    device.network = _create_mock_network()
    device.location = _create_mock_location(
        location_id=location_id,
        name=location_name,
        external_endpoint=external_endpoint,
        internal_endpoint=internal_endpoint,
    )
    device.external_endpoint_host, device.external_endpoint_port = _split_endpoint(
        external_endpoint
    )
    device.internal_endpoint_host, device.internal_endpoint_port = _split_endpoint(
        internal_endpoint
    )
    device.network.locations.append(device.location)

    return device


@pytest.fixture
def golden_dir() -> Path:
    """Get the directory containing golden configuration files."""
    return Path(__file__).parent / "golden" / "device_configs"


@pytest.fixture
def device_config_service() -> DeviceConfigService:
    """Create a device config service with a mock database."""
    mock_db = MagicMock()
    return DeviceConfigService(mock_db)


@pytest.fixture
def mock_device_with_all_options(unlocked_master_password: str) -> MagicMock:
    """Create a mock device with all configuration options for mesh topology."""
    device = MagicMock()
    device.id = "test-device-id"
    device.name = "Test Device"
    device.wireguard_ip = "10.0.0.2"
    test_preshared_key = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    device.preshared_key_encrypted = encrypt_preshared_key(
        test_preshared_key, unlocked_master_password
    )

    device.network = _create_mock_network()
    device.network.dns_servers = "8.8.8.8,8.8.4.4"
    device.network.mtu = 1420
    device.network.persistent_keepalive = 25

    device.location = _create_mock_location(
        location_id="location-1",
        name="Location 1",
        external_endpoint="vpn.example.com:51820",
    )
    device.network.locations.append(device.location)

    location2 = _create_mock_location(
        location_id="location-2",
        name="Location 2",
        external_endpoint="vpn2.example.com:51820",
    )
    device.network.locations.append(location2)

    peer1 = _create_mock_device(
        device_id="peer-1-id",
        name="Peer Device 1",
        wireguard_ip="10.0.0.3",
        public_key="peer1_public_key_1234567890123456789012",
        location=device.location,
        external_endpoint="peer1.example.com:51820",
        internal_endpoint="192.168.1.10:51820",
    )

    peer2 = _create_mock_device(
        device_id="peer-2-id",
        name="Peer Device 2",
        wireguard_ip="10.0.0.4",
        public_key="peer2_public_key_9876543210987654321098",
        location=location2,
        external_endpoint="peer2.example.com:51820",
    )

    device.network.devices = [device, peer1, peer2]

    return device


@pytest.fixture
def mock_device_minimal() -> MagicMock:
    """Create a mock device with minimal configuration for mesh topology."""
    device = _create_test_device(
        external_endpoint="vpn.example.com:51820",
    )

    peer1 = _create_mock_device(
        device_id="peer-1-id",
        name="Peer Device 1",
        wireguard_ip="10.0.0.3",
        public_key="peer1_public_key_1234567890123456789012",
        location=device.location,
        external_endpoint="peer1.example.com:51820",
    )

    device.network.devices = [device, peer1]

    return device


@pytest.fixture
def mock_device_same_location() -> MagicMock:
    """Create a mock device with multiple peers all in the same location."""
    device = _create_test_device(
        external_endpoint="vpn.example.com:51820",
        internal_endpoint="10.0.1.1:51820",
    )

    peer1 = _create_mock_device(
        device_id="peer-1-id",
        name="Peer Device 1",
        wireguard_ip="10.0.0.3",
        public_key="peer1_public_key_1234567890123456789012",
        location=device.location,
        external_endpoint="10.0.1.2:51820",
        internal_endpoint="10.0.1.2:51820",
    )

    peer2 = _create_mock_device(
        device_id="peer-2-id",
        name="Peer Device 2",
        wireguard_ip="10.0.0.4",
        public_key="peer2_public_key_9876543210987654321098",
        location=device.location,
        external_endpoint="10.0.1.3:51820",
        internal_endpoint="10.0.1.3:51820",
    )

    device.network.devices = [device, peer1, peer2]

    return device


@pytest.fixture
def mock_device_different_locations() -> MagicMock:
    """Create a mock device with peers all in different locations."""
    device = _create_test_device(
        external_endpoint="vpn1.example.com:51820",
        internal_endpoint="10.0.1.1:51820",
    )

    location2 = _create_mock_location(
        location_id="location-2",
        name="Location 2",
        external_endpoint="vpn2.example.com:51820",
    )
    device.network.locations.append(location2)

    location3 = _create_mock_location(
        location_id="location-3",
        name="Location 3",
        external_endpoint="vpn3.example.com:51820",
    )
    device.network.locations.append(location3)

    peer2 = _create_mock_device(
        device_id="peer-2-id",
        name="Peer Device 2",
        wireguard_ip="10.0.0.3",
        public_key="peer2_public_key_9876543210987654321098",
        location=location2,
        external_endpoint="vpn2.example.com:51820",
    )

    peer3 = _create_mock_device(
        device_id="peer-3-id",
        name="Peer Device 3",
        wireguard_ip="10.0.0.4",
        public_key="peer3_public_key_1111111111111111111111",
        location=location3,
        external_endpoint="vpn3.example.com:51820",
    )

    device.network.devices = [device, peer2, peer3]

    return device


@pytest.fixture
def mock_device_disabled_peer() -> MagicMock:
    """Create a mock device with a disabled peer that should be excluded."""
    device = _create_test_device(
        external_endpoint="vpn.example.com:51820",
    )

    peer1 = _create_mock_device(
        device_id="peer-1-id",
        name="Peer Device 1",
        wireguard_ip="10.0.0.3",
        public_key="peer1_public_key_1234567890123456789012",
        location=device.location,
        external_endpoint="peer1.example.com:51820",
    )

    peer2 = _create_mock_device(
        device_id="peer-2-id",
        name="Disabled Peer",
        wireguard_ip="10.0.0.4",
        public_key="peer2_public_key_9876543210987654321098",
        location=device.location,
        enabled=False,
        external_endpoint="peer2.example.com:51820",
    )

    device.network.devices = [device, peer1, peer2]

    return device


@pytest.fixture
def mock_device_network_psk(unlocked_master_password: str) -> MagicMock:
    """Create a mock device using network-level preshared key."""
    network_psk = "b0w7ipX1SXZ/dwOqP9iSQxydgFDIt/O7L4vz2hJW54E="

    device = _create_test_device(
        external_endpoint="vpn.example.com:51820",
    )
    device.network.preshared_key_encrypted = encrypt_preshared_key(
        network_psk, unlocked_master_password
    )

    peer1 = _create_mock_device(
        device_id="peer-1-id",
        name="Peer Device 1",
        wireguard_ip="10.0.0.3",
        public_key="peer1_public_key_1234567890123456789012",
        location=device.location,
        external_endpoint="peer1.example.com:51820",
    )

    device.network.devices = [device, peer1]

    return device


@pytest.mark.asyncio
async def test_device_config_wg_format_golden(
    device_config_service: DeviceConfigService,
    mock_device_with_all_options: MagicMock,
    golden_dir: Path,
) -> None:
    config_response = await device_config_service.generate_device_config(
        device=mock_device_with_all_options,
        device_private_key="test_private_key",  # pragma: allowlist secret
        format_type="wg",
    )

    golden_file = golden_dir / "sample_device_wg.conf"
    assert golden_file.exists(), f"Golden file not found: {golden_file}"

    expected_config = golden_file.read_text().strip()
    actual_config = str(config_response.configuration).strip()

    assert actual_config == expected_config, (
        f"Generated WireGuard config does not match golden file.\n"
        f"Expected:\n{expected_config}\n\n"
        f"Actual:\n{actual_config}"
    )


@pytest.mark.asyncio
async def test_device_config_mobile_format_golden(
    device_config_service: DeviceConfigService,
    mock_device_with_all_options: MagicMock,
    golden_dir: Path,
) -> None:
    config_response = await device_config_service.generate_device_config(
        device=mock_device_with_all_options,
        device_private_key="test_private_key",  # pragma: allowlist secret
        format_type="mobile",
        platform="ios",
    )

    golden_file = golden_dir / "sample_device_mobile.json"
    assert golden_file.exists(), f"Golden file not found: {golden_file}"

    expected_config = golden_file.read_text().strip()
    actual_config = config_response.configuration.model_dump_json(indent=2).strip()  # type: ignore[union-attr]

    assert actual_config == expected_config, (
        f"Generated mobile config does not match golden file.\n"
        f"Expected:\n{expected_config}\n\n"
        f"Actual:\n{actual_config}"
    )


@pytest.mark.asyncio
async def test_device_config_minimal_golden(
    device_config_service: DeviceConfigService,
    mock_device_minimal: MagicMock,
    golden_dir: Path,
) -> None:
    config_response = await device_config_service.generate_device_config(
        device=mock_device_minimal,
        device_private_key="test_private_key",  # pragma: allowlist secret
        format_type="wg",
    )

    golden_file = golden_dir / "sample_device_no_dns.conf"
    assert golden_file.exists(), f"Golden file not found: {golden_file}"

    expected_config = golden_file.read_text().strip()
    actual_config = str(config_response.configuration).strip()

    assert actual_config == expected_config, (
        f"Generated minimal config does not match golden file.\n"
        f"Expected:\n{expected_config}\n\n"
        f"Actual:\n{actual_config}"
    )


@pytest.mark.asyncio
async def test_device_config_same_location_golden(
    device_config_service: DeviceConfigService,
    mock_device_same_location: MagicMock,
    golden_dir: Path,
) -> None:
    config_response = await device_config_service.generate_device_config(
        device=mock_device_same_location,
        device_private_key="test_private_key",  # pragma: allowlist secret
        format_type="wg",
    )

    golden_file = golden_dir / "sample_device_same_location.conf"
    assert golden_file.exists(), f"Golden file not found: {golden_file}"

    expected_config = golden_file.read_text().strip()
    actual_config = str(config_response.configuration).strip()

    assert "10.0.1.2:51820" in actual_config, "Should use internal endpoint for peer1"
    assert "10.0.1.3:51820" in actual_config, "Should use internal endpoint for peer2"

    assert actual_config == expected_config, (
        f"Generated same-location config does not match golden file.\n"
        f"Expected:\n{expected_config}\n\n"
        f"Actual:\n{actual_config}"
    )


@pytest.mark.asyncio
async def test_device_config_different_locations_golden(
    device_config_service: DeviceConfigService,
    mock_device_different_locations: MagicMock,
    golden_dir: Path,
) -> None:
    config_response = await device_config_service.generate_device_config(
        device=mock_device_different_locations,
        device_private_key="test_private_key",  # pragma: allowlist secret
        format_type="wg",
    )

    golden_file = golden_dir / "sample_device_different_locations.conf"
    assert golden_file.exists(), f"Golden file not found: {golden_file}"

    expected_config = golden_file.read_text().strip()
    actual_config = str(config_response.configuration).strip()

    assert (
        "vpn2.example.com:51820" in actual_config
    ), "Should use external endpoint for peer2"
    assert (
        "vpn3.example.com:51820" in actual_config
    ), "Should use external endpoint for peer3"

    assert actual_config == expected_config, (
        f"Generated different-locations config does not match golden file.\n"
        f"Expected:\n{expected_config}\n\n"
        f"Actual:\n{actual_config}"
    )


@pytest.mark.asyncio
async def test_device_config_disabled_peer_golden(
    device_config_service: DeviceConfigService,
    mock_device_disabled_peer: MagicMock,
    golden_dir: Path,
) -> None:
    config_response = await device_config_service.generate_device_config(
        device=mock_device_disabled_peer,
        device_private_key="test_private_key",  # pragma: allowlist secret
        format_type="wg",
    )

    golden_file = golden_dir / "sample_device_disabled_peer.conf"
    assert golden_file.exists(), f"Golden file not found: {golden_file}"

    expected_config = golden_file.read_text().strip()
    actual_config = str(config_response.configuration).strip()

    assert "Disabled Peer" not in actual_config, "Disabled peer should be excluded"
    assert (
        "peer2_public_key_9876543210987654321098" not in actual_config
    ), "Disabled peer key should be excluded"

    assert actual_config == expected_config, (
        f"Generated disabled-peer config does not match golden file.\n"
        f"Expected:\n{expected_config}\n\n"
        f"Actual:\n{actual_config}"
    )


@pytest.mark.asyncio
async def test_device_config_network_psk_golden(
    device_config_service: DeviceConfigService,
    mock_device_network_psk: MagicMock,
    golden_dir: Path,
) -> None:
    config_response = await device_config_service.generate_device_config(
        device=mock_device_network_psk,
        device_private_key="test_private_key",  # pragma: allowlist secret
        format_type="wg",
    )

    golden_file = golden_dir / "sample_device_network_psk.conf"
    assert golden_file.exists(), f"Golden file not found: {golden_file}"

    expected_config = golden_file.read_text().strip()
    actual_config = str(config_response.configuration).strip()

    assert (
        "PresharedKey = b0w7ipX1SXZ/dwOqP9iSQxydgFDIt/O7L4vz2hJW54E=" in actual_config
    )

    assert actual_config == expected_config, (
        f"Generated network-PSK config does not match golden file.\n"
        f"Expected:\n{expected_config}\n\n"
        f"Actual:\n{actual_config}"
    )


def test_update_golden_files(
    device_config_service: DeviceConfigService,
    mock_device_with_all_options: MagicMock,
    mock_device_minimal: MagicMock,
    mock_device_same_location: MagicMock,
    mock_device_different_locations: MagicMock,
    mock_device_disabled_peer: MagicMock,
    mock_device_network_psk: MagicMock,
    golden_dir: Path,
) -> None:
    print("\n=== UPDATING GOLDEN FILES ===")

    config_response = asyncio.run(
        device_config_service.generate_device_config(
            device=mock_device_with_all_options,
            device_private_key="test_private_key",  # pragma: allowlist secret
            format_type="wg",
        )
    )
    (golden_dir / "sample_device_wg.conf").write_text(
        str(config_response.configuration)
    )
    print("Updated: sample_device_wg.conf")

    config_response = asyncio.run(
        device_config_service.generate_device_config(
            device=mock_device_with_all_options,
            device_private_key="test_private_key",  # pragma: allowlist secret
            format_type="mobile",
            platform="ios",
        )
    )
    (golden_dir / "sample_device_mobile.json").write_text(
        config_response.configuration.model_dump_json(indent=2)  # type: ignore[union-attr]
    )
    print("Updated: sample_device_mobile.json")

    config_response = asyncio.run(
        device_config_service.generate_device_config(
            device=mock_device_minimal,
            device_private_key="test_private_key",  # pragma: allowlist secret
            format_type="wg",
        )
    )
    (golden_dir / "sample_device_no_dns.conf").write_text(
        str(config_response.configuration)
    )
    print("Updated: sample_device_no_dns.conf")

    config_response = asyncio.run(
        device_config_service.generate_device_config(
            device=mock_device_same_location,
            device_private_key="test_private_key",  # pragma: allowlist secret
            format_type="wg",
        )
    )
    (golden_dir / "sample_device_same_location.conf").write_text(
        str(config_response.configuration)
    )
    print("Updated: sample_device_same_location.conf")

    config_response = asyncio.run(
        device_config_service.generate_device_config(
            device=mock_device_different_locations,
            device_private_key="test_private_key",  # pragma: allowlist secret
            format_type="wg",
        )
    )
    (golden_dir / "sample_device_different_locations.conf").write_text(
        str(config_response.configuration)
    )
    print("Updated: sample_device_different_locations.conf")

    config_response = asyncio.run(
        device_config_service.generate_device_config(
            device=mock_device_disabled_peer,
            device_private_key="test_private_key",  # pragma: allowlist secret
            format_type="wg",
        )
    )
    (golden_dir / "sample_device_disabled_peer.conf").write_text(
        str(config_response.configuration)
    )
    print("Updated: sample_device_disabled_peer.conf")

    config_response = asyncio.run(
        device_config_service.generate_device_config(
            device=mock_device_network_psk,
            device_private_key="test_private_key",  # pragma: allowlist secret
            format_type="wg",
        )
    )
    (golden_dir / "sample_device_network_psk.conf").write_text(
        str(config_response.configuration)
    )
    print("Updated: sample_device_network_psk.conf")

    print("=== GOLDEN FILES UPDATED ===")


if __name__ == "__main__":
    # Allow running this file directly to update golden files
    import sys

    sys.exit(pytest.main([__file__, "-k", "test_update_golden_files", "-s"]))
