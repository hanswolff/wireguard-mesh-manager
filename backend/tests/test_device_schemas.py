"""Tests for device schema validation."""

from __future__ import annotations

import pytest

from app.schemas.devices import DeviceCreate, DeviceUpdate


class TestDeviceCreateEndpointValidation:
    """Test DeviceCreate endpoint validation."""

    def test_valid_external_endpoint(self) -> None:
        """Test valid external endpoints."""
        valid_endpoints = [
            ("192.168.1.100", 51820),
            ("vpn.example.com", 51820),
            ("[2001:db8::1]", 51820),
            ("my-wireguard-server.com", 12345),
            ("10.0.0.1", 80),
        ]

        for host, port in valid_endpoints:
            device_data = {
                "network_id": "network-1",
                "location_id": "location-1",
                "name": "test-device",
                "public_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
                "private_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
                "external_endpoint_host": host,
                "external_endpoint_port": port,
            }
            device = DeviceCreate(**device_data)
            assert device.external_endpoint_host == host
            assert device.external_endpoint_port == port

    def test_valid_internal_endpoint(self) -> None:
        """Test valid internal endpoints."""
        valid_endpoints = [
            ("192.168.1.100", 51820),
            ("10.0.0.1", 51820),
            ("172.16.0.1", 51820),
            ("vpn.internal", 51820),
        ]

        for host, port in valid_endpoints:
            device_data = {
                "network_id": "network-1",
                "location_id": "location-1",
                "name": "test-device",
                "public_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
                "private_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
                "internal_endpoint_host": host,
                "internal_endpoint_port": port,
            }
            device = DeviceCreate(**device_data)
            assert device.internal_endpoint_host == host
            assert device.internal_endpoint_port == port

    def test_both_endpoints(self) -> None:
        """Test device with both endpoints."""
        device_data = {
            "network_id": "network-1",
            "location_id": "location-1",
            "name": "test-device",
            "public_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "private_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "external_endpoint_host": "vpn.example.com",
            "external_endpoint_port": 51820,
            "internal_endpoint_host": "192.168.1.100",
            "internal_endpoint_port": 51820,
        }
        device = DeviceCreate(**device_data)
        assert device.external_endpoint_host == "vpn.example.com"
        assert device.external_endpoint_port == 51820
        assert device.internal_endpoint_host == "192.168.1.100"
        assert device.internal_endpoint_port == 51820

    def test_null_endpoints(self) -> None:
        """Test device with null endpoints now requires at least one port."""
        device_data = {
            "network_id": "network-1",
            "location_id": "location-1",
            "name": "test-device",
            "public_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "private_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
        }
        # With the new requirement, at least one port must be provided
        with pytest.raises(ValueError, match="At least one port .* must be provided"):
            DeviceCreate(**device_data)

    def test_invalid_external_endpoint_no_port(self) -> None:
        """Test external endpoint without port."""
        device_data = {
            "network_id": "network-1",
            "location_id": "location-1",
            "name": "test-device",
            "public_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "external_endpoint_host": "192.168.1.100",
        }
        # This should fail because host requires port AND no other port is provided
        with pytest.raises(
            ValueError, match="External endpoint host requires a port"
        ):
            DeviceCreate(**device_data)

    def test_invalid_internal_endpoint_no_host(self) -> None:
        """Test internal endpoint without host."""
        device_data = {
            "network_id": "network-1",
            "location_id": "location-1",
            "name": "test-device",
            "public_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "internal_endpoint_port": 51820,
        }
        with pytest.raises(ValueError, match="Internal endpoint requires both host and port"):
            DeviceCreate(**device_data)

    def test_invalid_internal_endpoint_no_port(self) -> None:
        """Test internal endpoint without port."""
        device_data = {
            "network_id": "network-1",
            "location_id": "location-1",
            "name": "test-device",
            "public_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "internal_endpoint_host": "192.168.1.100",
        }
        with pytest.raises(ValueError, match="Internal endpoint requires both host and port"):
            DeviceCreate(**device_data)

    def test_invalid_endpoint_port_too_high(self) -> None:
        """Test endpoint with port too high."""
        device_data = {
            "network_id": "network-1",
            "location_id": "location-1",
            "name": "test-device",
            "public_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "external_endpoint_host": "192.168.1.100",
            "external_endpoint_port": 99999,
        }
        with pytest.raises(ValueError, match="Port must be an integer between 1 and 65535"):
            DeviceCreate(**device_data)

    def test_invalid_endpoint_port_zero(self) -> None:
        """Test endpoint with port zero."""
        device_data = {
            "network_id": "network-1",
            "location_id": "location-1",
            "name": "test-device",
            "public_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "internal_endpoint_host": "192.168.1.100",
            "internal_endpoint_port": 0,
        }
        with pytest.raises(ValueError, match="Port must be an integer between 1 and 65535"):
            DeviceCreate(**device_data)

    def test_invalid_endpoint_non_numeric_port(self) -> None:
        """Test endpoint with non-numeric port."""
        device_data = {
            "network_id": "network-1",
            "location_id": "location-1",
            "name": "test-device",
            "public_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "external_endpoint_host": "192.168.1.100",
            "external_endpoint_port": "abc",
        }
        with pytest.raises(ValueError, match="Port must be an integer between 1 and 65535"):
            DeviceCreate(**device_data)

    def test_invalid_endpoint_float_port(self) -> None:
        """Test endpoint with a float port."""
        device_data = {
            "network_id": "network-1",
            "location_id": "location-1",
            "name": "test-device",
            "public_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "external_endpoint_host": "192.168.1.100",
            "external_endpoint_port": 51820.5,
        }
        with pytest.raises(ValueError, match="Port must be an integer between 1 and 65535"):
            DeviceCreate(**device_data)

    def test_empty_string_endpoint_treated_as_none(self) -> None:
        """Test that empty string endpoint is converted to None (but at least one port required)."""
        device_data = {
            "network_id": "network-1",
            "location_id": "location-1",
            "name": "test-device",
            "public_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "private_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "external_endpoint_host": "",
            # Must provide at least one port (with host for internal endpoint)
            "internal_endpoint_host": "192.168.1.100",
            "internal_endpoint_port": 51820,
        }
        device = DeviceCreate(**device_data)
        assert device.external_endpoint_host is None
        assert device.internal_endpoint_host == "192.168.1.100"
        assert device.internal_endpoint_port == 51820

    def test_ipv6_endpoint_with_brackets(self) -> None:
        """Test IPv6 endpoint with brackets."""
        device_data = {
            "network_id": "network-1",
            "location_id": "location-1",
            "name": "test-device",
            "public_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "private_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "external_endpoint_host": "[2001:db8::1]",
            "external_endpoint_port": 51820,
        }
        device = DeviceCreate(**device_data)
        assert device.external_endpoint_host == "[2001:db8::1]"
        assert device.external_endpoint_port == 51820

    def test_hostname_endpoint(self) -> None:
        """Test hostname endpoint."""
        device_data = {
            "network_id": "network-1",
            "location_id": "location-1",
            "name": "test-device",
            "public_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "private_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "internal_endpoint_host": "vpn-server",
            "internal_endpoint_port": 51820,
        }
        device = DeviceCreate(**device_data)
        assert device.internal_endpoint_host == "vpn-server"
        assert device.internal_endpoint_port == 51820

    def test_domain_endpoint(self) -> None:
        """Test domain name endpoint."""
        device_data = {
            "network_id": "network-1",
            "location_id": "location-1",
            "name": "test-device",
            "public_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "private_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "external_endpoint_host": "my-wireguard.example.org",
            "external_endpoint_port": 12345,
        }
        device = DeviceCreate(**device_data)
        assert device.external_endpoint_host == "my-wireguard.example.org"
        assert device.external_endpoint_port == 12345

    def test_external_port_without_host_allowed(self) -> None:
        """Test external endpoint port without explicit host."""
        device_data = {
            "network_id": "network-1",
            "location_id": "location-1",
            "name": "test-device",
            "public_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "private_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "external_endpoint_port": 51820,
        }
        device = DeviceCreate(**device_data)
        assert device.external_endpoint_host is None
        assert device.external_endpoint_port == 51820

    def test_at_least_one_port_required_for_device_create(self) -> None:
        """Test that at least one port (internal or external) must be provided."""
        device_data = {
            "network_id": "network-1",
            "location_id": "location-1",
            "name": "test-device",
            "public_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "private_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            # No ports provided
        }
        with pytest.raises(
            ValueError, match="At least one port .* must be provided"
        ):
            DeviceCreate(**device_data)

    def test_internal_port_only_allowed(self) -> None:
        """Test that providing only internal port is valid."""
        device_data = {
            "network_id": "network-1",
            "location_id": "location-1",
            "name": "test-device",
            "public_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "private_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "internal_endpoint_host": "192.168.1.100",
            "internal_endpoint_port": 51820,
        }
        device = DeviceCreate(**device_data)
        assert device.internal_endpoint_host == "192.168.1.100"
        assert device.internal_endpoint_port == 51820
        assert device.external_endpoint_port is None

    def test_external_port_only_allowed(self) -> None:
        """Test that providing only external port is valid."""
        device_data = {
            "network_id": "network-1",
            "location_id": "location-1",
            "name": "test-device",
            "public_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "private_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "external_endpoint_host": "vpn.example.com",
            "external_endpoint_port": 51820,
        }
        device = DeviceCreate(**device_data)
        assert device.external_endpoint_host == "vpn.example.com"
        assert device.external_endpoint_port == 51820
        assert device.internal_endpoint_port is None


class TestDeviceUpdateEndpointValidation:
    """Test DeviceUpdate endpoint validation."""

    def test_valid_external_endpoint_update(self) -> None:
        """Test updating with valid external endpoint."""
        update_data = {
            "external_endpoint_host": "vpn.example.com",
            "external_endpoint_port": 51820,
        }
        device_update = DeviceUpdate(**update_data)
        assert device_update.external_endpoint_host == "vpn.example.com"
        assert device_update.external_endpoint_port == 51820

    def test_valid_internal_endpoint_update(self) -> None:
        """Test updating with valid internal endpoint."""
        update_data = {
            "internal_endpoint_host": "10.0.0.1",
            "internal_endpoint_port": 51820,
        }
        device_update = DeviceUpdate(**update_data)
        assert device_update.internal_endpoint_host == "10.0.0.1"
        assert device_update.internal_endpoint_port == 51820

    def test_both_endpoints_update(self) -> None:
        """Test updating with both endpoints."""
        update_data = {
            "external_endpoint_host": "vpn.example.com",
            "external_endpoint_port": 51820,
            "internal_endpoint_host": "192.168.1.100",
            "internal_endpoint_port": 51820,
        }
        device_update = DeviceUpdate(**update_data)
        assert device_update.external_endpoint_host == "vpn.example.com"
        assert device_update.external_endpoint_port == 51820
        assert device_update.internal_endpoint_host == "192.168.1.100"
        assert device_update.internal_endpoint_port == 51820

    def test_null_endpoints_update(self) -> None:
        """Test updating with null endpoints."""
        update_data = {
            "name": "updated-name",
        }
        device_update = DeviceUpdate(**update_data)
        assert device_update.external_endpoint_host is None
        assert device_update.external_endpoint_port is None
        assert device_update.internal_endpoint_host is None
        assert device_update.internal_endpoint_port is None

    def test_invalid_external_endpoint_update(self) -> None:
        """Test updating with invalid external endpoint."""
        update_data = {
            "external_endpoint_host": "invalid:endpoint",
            "external_endpoint_port": 51820,
        }
        with pytest.raises(ValueError, match="Invalid host format"):
            DeviceUpdate(**update_data)

    def test_invalid_internal_endpoint_update(self) -> None:
        """Test updating with invalid internal endpoint."""
        update_data = {
            "internal_endpoint_host": "192.168.1.100",
            "internal_endpoint_port": 99999,
        }
        with pytest.raises(ValueError, match="Port must be an integer between 1 and 65535"):
            DeviceUpdate(**update_data)

    def test_invalid_external_endpoint_float_update(self) -> None:
        """Test updating with a float external port."""
        update_data = {
            "external_endpoint_host": "vpn.example.com",
            "external_endpoint_port": 1234.5,
        }
        with pytest.raises(ValueError, match="Port must be an integer between 1 and 65535"):
            DeviceUpdate(**update_data)

    def test_set_endpoint_to_none(self) -> None:
        """Test setting endpoint explicitly to None."""
        update_data = {
            "external_endpoint_host": None,
            "external_endpoint_port": None,
        }
        device_update = DeviceUpdate(**update_data)
        assert device_update.external_endpoint_host is None
        assert device_update.external_endpoint_port is None

    def test_empty_string_endpoint_treated_as_none(self) -> None:
        """Test that empty string endpoint is converted to None (optional endpoint)."""
        update_data = {
            "internal_endpoint_host": "",
        }
        device_update = DeviceUpdate(**update_data)
        assert device_update.internal_endpoint_host is None

    def test_update_with_other_fields_and_endpoints(self) -> None:
        """Test updating with other fields along with endpoints."""
        update_data = {
            "name": "updated-name",
            "description": "Updated description",
            "external_endpoint_host": "vpn.example.com",
            "external_endpoint_port": 12345,
            "internal_endpoint_host": "10.0.0.1",
            "internal_endpoint_port": 54321,
            "enabled": False,
        }
        device_update = DeviceUpdate(**update_data)
        assert device_update.name == "updated-name"
        assert device_update.description == "Updated description"
        assert device_update.external_endpoint_host == "vpn.example.com"
        assert device_update.external_endpoint_port == 12345
        assert device_update.internal_endpoint_host == "10.0.0.1"
        assert device_update.internal_endpoint_port == 54321
        assert device_update.enabled is False


class TestEndpointFormatNormalization:
    """Test that endpoint formats are normalized."""

    def test_endpoint_with_whitespace(self) -> None:
        """Test that whitespace around endpoint is handled."""
        device_data = {
            "network_id": "network-1",
            "location_id": "location-1",
            "name": "test-device",
            "public_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "private_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "external_endpoint_host": " vpn.example.com ",
            "external_endpoint_port": 51820,
        }
        device = DeviceCreate(**device_data)
        assert device.external_endpoint_host == "vpn.example.com"
        assert device.external_endpoint_port == 51820

    def test_endpoint_preserves_original_format(self) -> None:
        """Test that valid endpoint format is preserved."""
        device_data = {
            "network_id": "network-1",
            "location_id": "location-1",
            "name": "test-device",
            "public_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "private_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "external_endpoint_host": "VPN.Example.COM",
            "external_endpoint_port": 51820,
        }
        device = DeviceCreate(**device_data)
        assert device.external_endpoint_host == "VPN.Example.COM"
        assert device.external_endpoint_port == 51820


class TestInterfacePropertiesValidation:
    """Test interface properties validation."""

    def test_valid_interface_properties(self) -> None:
        """Test valid interface properties."""
        device_data = {
            "network_id": "network-1",
            "location_id": "location-1",
            "name": "test-device",
            "public_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "private_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "internal_endpoint_host": "192.168.1.100",
            "internal_endpoint_port": 51820,
            "interface_properties": {"PostUp": "iptables -A FORWARD -i %i -j ACCEPT"},
        }
        device = DeviceCreate(**device_data)
        assert device.interface_properties == {
            "PostUp": "iptables -A FORWARD -i %i -j ACCEPT"
        }

    def test_interface_properties_with_newline(self) -> None:
        """Test that interface properties with newlines are rejected."""
        device_data = {
            "network_id": "network-1",
            "location_id": "location-1",
            "name": "test-device",
            "public_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "private_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "internal_endpoint_host": "192.168.1.100",
            "internal_endpoint_port": 51820,
            "interface_properties": {"PostUp": "iptables -A FORWARD -i %i -j ACCEPT\niptables -A FORWARD -o %i -j ACCEPT"},
        }
        with pytest.raises(ValueError, match="cannot contain line breaks"):
            DeviceCreate(**device_data)

    def test_interface_properties_with_carriage_return(self) -> None:
        """Test that interface properties with carriage returns are rejected."""
        device_data = {
            "network_id": "network-1",
            "location_id": "location-1",
            "name": "test-device",
            "public_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "private_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "internal_endpoint_host": "192.168.1.100",
            "internal_endpoint_port": 51820,
            "interface_properties": {"PostUp": "iptables -A FORWARD -i %i -j ACCEPT\riptables -A FORWARD -o %i -j ACCEPT"},
        }
        with pytest.raises(ValueError, match="cannot contain line breaks"):
            DeviceCreate(**device_data)

    def test_interface_properties_none(self) -> None:
        """Test that None interface properties are accepted."""
        device_data = {
            "network_id": "network-1",
            "location_id": "location-1",
            "name": "test-device",
            "public_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "private_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "internal_endpoint_host": "192.168.1.100",
            "internal_endpoint_port": 51820,
            "interface_properties": None,
        }
        device = DeviceCreate(**device_data)
        assert device.interface_properties is None

    def test_interface_properties_update_with_newline(self) -> None:
        """Test that updating interface properties with newlines is rejected."""
        update_data = {
            "interface_properties": {"PostUp": "iptables -A FORWARD -i %i -j ACCEPT\niptables -A FORWARD -o %i -j ACCEPT"},
        }
        with pytest.raises(ValueError, match="cannot contain line breaks"):
            DeviceUpdate(**update_data)
