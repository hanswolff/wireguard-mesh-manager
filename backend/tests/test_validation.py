"""Tests for validation utilities."""

from __future__ import annotations

import pytest

from app.utils.validation import (
    ValidationError,
    validate_dns_servers,
    validate_endpoint,
    validate_external_endpoint,
    validate_host,
    validate_mtu,
    validate_network_cidr,
    validate_peer_properties,
    validate_persistent_keepalive,
    validate_wireguard_public_key,
)


class TestEndpointValidation:
    """Test endpoint validation."""

    def test_valid_endpoints(self) -> None:
        """Test valid endpoint formats."""
        valid_endpoints = [
            "192.168.1.100:51820",
            "vpn.example.com:51820",
            "[2001:db8::1]:51820",
            "my-wireguard-server.com:12345",
            "10.0.0.1:80",
        ]

        for endpoint in valid_endpoints:
            host, port = validate_endpoint(endpoint)
            assert isinstance(host, str)
            assert isinstance(port, int)
            assert 1 <= port <= 65535

    def test_invalid_endpoints(self) -> None:
        """Test invalid endpoint formats."""
        invalid_endpoints = [
            "",  # Empty
            "192.168.1.100",  # No port
            "192.168.1.100:",  # Empty port
            ":51820",  # Empty host
            "192.168.1.100:99999",  # Port too high
            "192.168.1.100:0",  # Port too low
            "192.168.1.100:abc",  # Non-numeric port
            "192.168.1.100:51820:extra",  # Too many colons
        ]

        for endpoint in invalid_endpoints:
            with pytest.raises(ValidationError):
                validate_endpoint(endpoint)

    def test_ipv6_endpoints(self) -> None:
        """Test IPv6 endpoint validation."""
        # IPv6 with brackets
        host, port = validate_endpoint("[2001:db8::1]:51820")
        assert host == "[2001:db8::1]"
        assert port == 51820

        # IPv6 without brackets (ambiguous - will treat first part as host)
        host, port = validate_endpoint("2001:db8::1:51820")
        assert host == "2001:db8::1"
        assert port == 51820


class TestHostValidation:
    """Test host validation."""

    def test_valid_ipv4(self) -> None:
        """Test valid IPv4 addresses."""
        valid_ips = [
            "192.168.1.100",
            "10.0.0.1",
            "172.16.0.1",
            "1.2.3.4",
            "255.255.255.255",
        ]

        for ip in valid_ips:
            validate_host(ip)  # Should not raise

    def test_invalid_ipv4(self) -> None:
        """Test invalid IPv4 addresses."""
        invalid_ips = [
            "256.1.1.1",  # Octet too high
            "192.168.1",  # Not enough octets
            "192.168.1.1.1",  # Too many octets
            "192.168.1.a",  # Non-numeric
            "",  # Empty
        ]

        for ip in invalid_ips:
            with pytest.raises(ValidationError):
                validate_host(ip)

    def test_edge_case_ipv4(self) -> None:
        """Test edge case IPv4 addresses."""
        # These should be valid even if they're special addresses
        edge_ips = [
            "255.255.255.255",  # Broadcast address
            "0.0.0.0",  # Unspecified address
        ]

        for ip in edge_ips:
            validate_host(ip)  # Should not raise

    def test_valid_domain_names(self) -> None:
        """Test valid domain names."""
        valid_domains = [
            "example.com",
            "vpn.example.com",
            "my-wireguard-server.org",
            "test.co.uk",
            "a.b.c.d.e.f.g",
        ]

        for domain in valid_domains:
            validate_host(domain)  # Should not raise

    def test_invalid_domain_names(self) -> None:
        """Test invalid domain names."""
        invalid_domains = [
            ".example.com",  # Starts with dot
            "example.com.",  # Ends with dot
            "example..com",  # Double dot
            "-example.com",  # Starts with hyphen
            "example-.com",  # Ends with hyphen
            "",  # Empty
            "a" * 254,  # Too long
        ]

        for domain in invalid_domains:
            with pytest.raises(ValidationError):
                validate_host(domain)

    def test_valid_hostnames(self) -> None:
        """Test valid hostnames (no domain)."""
        valid_hostnames = [
            "server",
            "vpn-server",
            "test123",
            "a",
        ]

        for hostname in valid_hostnames:
            validate_host(hostname)  # Should not raise

    def test_invalid_hostnames(self) -> None:
        """Test invalid hostnames."""
        invalid_hostnames = [
            "-server",
            "server-",
            "a" * 64,  # Too long
            "",
        ]

        for hostname in invalid_hostnames:
            with pytest.raises(ValidationError):
                validate_host(hostname)

    def test_ipv6_with_brackets(self) -> None:
        """Test IPv6 addresses with brackets."""
        valid_ipv6 = [
            "[2001:db8::1]",
            "[::1]",
            "[2001:db8:85a3::8a2e:370:7334]",
        ]

        for ipv6 in valid_ipv6:
            validate_host(ipv6)  # Should not raise

    def test_invalid_ipv6_with_brackets(self) -> None:
        """Test invalid IPv6 addresses with brackets."""
        invalid_ipv6 = [
            "[2001:db8::1",  # Missing closing bracket
            "2001:db8::1]",  # Missing opening bracket
            "[2001:db8:::1]",  # Too many colons
            "[2001:db8::g]",  # Invalid hex character
        ]

        for ipv6 in invalid_ipv6:
            with pytest.raises(ValidationError):
                validate_host(ipv6)


class TestNetworkCIDRValidation:
    """Test network CIDR validation."""

    def test_valid_cidr(self) -> None:
        """Test valid CIDR notations."""
        valid_cidrs = [
            "10.0.0.0/24",
            "192.168.1.0/24",
            "172.16.0.0/16",
            "192.168.1.100/32",
        ]

        for cidr in valid_cidrs:
            validate_network_cidr(cidr)  # Should not raise

    def test_invalid_cidr(self) -> None:
        """Test invalid CIDR notations."""
        invalid_cidrs = [
            "",  # Empty
            "10.0.0.0",  # Missing prefix
            "10.0.0.0/",  # Missing prefix length
            "10.0.0.0/33",  # Prefix too high
            "10.0.0.0/7",  # Prefix too low for our validation
            "256.0.0.0/24",  # Invalid IP
            "10.0.0.256/24",  # Invalid IP
            "10.0.0.0.0/24",  # Too many octets
            "10.0.0/24",  # Not enough octets
            "10.0.0.0/abc",  # Non-numeric prefix
        ]

        for cidr in invalid_cidrs:
            with pytest.raises(ValidationError):
                validate_network_cidr(cidr)


class TestWireGuardPublicKeyValidation:
    """Test WireGuard public key validation."""

    def test_valid_public_keys(self) -> None:
        """Test valid WireGuard public keys."""
        # Use valid base64 44-character strings
        valid_keys = [
            "cGxlYXN1cmUuaW5zZXJ0c29tZXRleHRoZXJlaGVyZWJlY2F1c2VpdHM=",  # pragma: allowlist secret
        ]

        for key in valid_keys:
            validate_wireguard_public_key(key)  # Should not raise

    def test_invalid_public_keys(self) -> None:
        """Test invalid WireGuard public keys."""
        invalid_keys = [
            "",  # Empty
            "too_short",  # Too short
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzz",  # pragma: allowlist secret
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwx!",  # Invalid character
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvw",  # Too short (43 chars)
        ]

        for key in invalid_keys:
            with pytest.raises(ValidationError):
                validate_wireguard_public_key(key)


class TestDnsServersValidation:
    """Test DNS servers validation."""

    def test_valid_dns_servers(self) -> None:
        """Test valid DNS server lists."""
        valid_dns = [
            "8.8.8.8",
            "8.8.8.8,8.8.4.4",
            "1.1.1.1,1.0.0.1",
            "dns.example.com",
            "8.8.8.8,dns.example.com",
            "8.8.8.8 , 8.8.4.4 , dns.example.com",  # With spaces
        ]

        for dns in valid_dns:
            validate_dns_servers(dns)  # Should not raise

    def test_invalid_dns_servers(self) -> None:
        """Test invalid DNS server lists."""
        invalid_dns = [
            "256.1.1.1",  # Invalid IP
            "-invalid",  # Invalid hostname (starts with hyphen)
            "8.8.8.8,-invalid",  # Mixed valid/invalid
            ",",  # Empty entry
            "8.8.8.8,.com",  # Invalid domain entry (starts with dot)
        ]

        for dns in invalid_dns:
            with pytest.raises(ValidationError):
                validate_dns_servers(dns)

    def test_empty_dns_servers(self) -> None:
        """Test empty DNS servers."""
        validate_dns_servers(None)  # Should not raise
        validate_dns_servers("")  # Should not raise (empty string)


class TestMtuValidation:
    """Test MTU validation."""

    def test_valid_mtu(self) -> None:
        """Test valid MTU values."""
        valid_mtus = [576, 1500, 9000, 1420]

        for mtu in valid_mtus:
            validate_mtu(mtu)  # Should not raise

    def test_invalid_mtu(self) -> None:
        """Test invalid MTU values."""
        invalid_mtus = [575, 9001, 0, -1, 3.14, "1500"]

        for mtu in invalid_mtus:
            with pytest.raises(ValidationError):
                validate_mtu(mtu)  # type: ignore[arg-type]

    def test_none_mtu(self) -> None:
        """Test None MTU."""
        validate_mtu(None)  # Should not raise


class TestPersistentKeepaliveValidation:
    """Test persistent keepalive validation."""

    def test_valid_keepalive(self) -> None:
        """Test valid keepalive values."""
        valid_values = [0, 25, 60, 300, 86400]

        for value in valid_values:
            validate_persistent_keepalive(value)  # Should not raise

    def test_invalid_keepalive(self) -> None:
        """Test invalid keepalive values."""
        invalid_values = [-1, 86401, 3.14, "25"]

        for value in invalid_values:
            with pytest.raises(ValidationError):
                validate_persistent_keepalive(value)  # type: ignore[arg-type]

    def test_none_keepalive(self) -> None:
        """Test None keepalive."""
        validate_persistent_keepalive(None)  # Should not raise


class TestPeerPropertiesValidation:
    """Test peer property validation."""

    def test_valid_peer_properties(self) -> None:
        """Valid peer properties should pass."""
        validate_peer_properties(
            {"PersistentKeepalive": 25, "Note": "Backhaul", "Metric": 2}
        )

    def test_invalid_peer_properties_keys(self) -> None:
        """Reserved or malformed keys should fail."""
        invalid_properties = [
            {"PublicKey": "oops"},
            {"AllowedIPs": "10.0.0.0/24"},
            {"Bad-Key": "nope"},
            {"": "empty"},
        ]
        for properties in invalid_properties:
            with pytest.raises(ValidationError):
                validate_peer_properties(properties)


class TestExternalEndpointValidation:
    """Test external endpoint validation with security rules."""

    def test_public_ip_allowed(self) -> None:
        """Test that public IPs are allowed."""
        valid_endpoints = [
            "1.2.3.4:51820",
            "8.8.8.8:53",
            "vpn.example.com:51820",
        ]

        for endpoint in valid_endpoints:
            validate_external_endpoint(
                endpoint, allow_private=False
            )  # Should not raise

    def test_private_ip_allowed_when_flag_set(self) -> None:
        """Test that private IPs are allowed when flag is set."""
        private_endpoints = [
            "192.168.1.100:51820",
            "10.0.0.1:51820",
            "172.16.0.1:51820",
        ]

        for endpoint in private_endpoints:
            validate_external_endpoint(endpoint, allow_private=True)  # Should not raise

    def test_private_ip_blocked_when_flag_not_set(self) -> None:
        """Test that private IPs are blocked when flag is not set."""
        private_endpoints = [
            "192.168.1.100:51820",
            "10.0.0.1:51820",
            "172.16.0.1:51820",
            "127.0.0.1:51820",  # Loopback
        ]

        for endpoint in private_endpoints:
            with pytest.raises(ValidationError, match="private IP"):
                validate_external_endpoint(endpoint, allow_private=False)
