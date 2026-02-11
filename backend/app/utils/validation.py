"""Validation utilities for common input formats."""

from __future__ import annotations

import ipaddress
import re


class ValidationError(Exception):
    """Custom validation error for better error messages."""

    pass


# Compile regex patterns once for efficiency
DOMAIN_NAME_PATTERN = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z]{2,})+$"
)
HOSTNAME_PATTERN = re.compile(r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)$")
# IPv6 patterns
IPv6_WITH_BRACKETS_PATTERN = re.compile(r"^\[[0-9a-fA-F:]+\]$")
IPv6_NO_BRACKETS_PATTERN = re.compile(r"^[0-9a-fA-F:]+$")


def validate_endpoint(endpoint: str) -> tuple[str, int]:
    """
    Validate and parse an endpoint string (host:port).

    Args:
        endpoint: Endpoint string in format "host:port"

    Returns:
        Tuple of (host, port)

    Raises:
        ValidationError: If endpoint format is invalid
    """
    if not endpoint or not isinstance(endpoint, str):
        raise ValidationError("Endpoint cannot be empty")

    # Basic format validation
    if ":" not in endpoint:
        raise ValidationError("Endpoint must contain ':' to separate host and port")

    # Split on last colon to handle IPv6 addresses
    parts = endpoint.rsplit(":", 1)
    if len(parts) != 2:
        raise ValidationError("Endpoint must be in format 'host:port'")

    host, port_str = parts[0].strip(), parts[1].strip()

    # Validate and parse port
    try:
        port = int(port_str)
        if not 1 <= port <= 65535:
            raise ValidationError(f"Port must be between 1 and 65535, got {port}")
    except ValueError as e:
        raise ValidationError(f"Port must be a valid integer, got '{port_str}'") from e

    # Validate host
    validate_host(host)

    return host, port


def validate_port(port: int) -> int:
    """
    Validate a port number.

    Args:
        port: Port value to validate

    Returns:
        Validated port value

    Raises:
        ValidationError: If port is invalid
    """
    if not isinstance(port, int):
        raise ValidationError("Port must be an integer")
    if not 1 <= port <= 65535:
        raise ValidationError(f"Port must be between 1 and 65535, got {port}")
    return port


def validate_host(host: str) -> None:
    """
    Validate a hostname or IP address.

    Args:
        host: Host string to validate

    Raises:
        ValidationError: If host format is invalid
    """
    if not host or not isinstance(host, str):
        raise ValidationError("Host cannot be empty")

    # Try IP address validation first
    if _is_ip_address(host):
        return  # Valid IP address

    # Try IPv6 with brackets
    if host.startswith("[") and host.endswith("]"):
        ipv6_host = host[1:-1]
        if _is_ipv6_address(ipv6_host):
            return  # Valid IPv6 address with brackets
        else:
            raise ValidationError(f"Invalid IPv6 address in brackets: {host}")

    # Try domain name validation
    if _is_domain_name(host):
        return  # Valid domain name

    # Try simple hostname validation
    if _is_hostname(host):
        return  # Valid hostname

    raise ValidationError(f"Invalid host format: {host}")


def _is_ip_address(host: str) -> bool:
    """Check if string is a valid IP address (IPv4 or IPv6)."""
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def _is_ipv4_address(host: str) -> bool:
    """Check if string is a valid IPv4 address."""
    try:
        ipaddress.IPv4Address(host)
        return True
    except ValueError:
        return False


def _is_ipv6_address(host: str) -> bool:
    """Check if string is a valid IPv6 address."""
    try:
        ipaddress.IPv6Address(host)
        return True
    except ValueError:
        return False


def _is_domain_name(host: str) -> bool:
    """Check if string is a valid domain name."""
    if len(host) > 253:
        return False

    # Simplified domain validation - allow more flexible but still valid domains
    if "." not in host:
        return False

    # First check if it looks like an IP address (should not be considered a domain)
    if _looks_like_ip_address(host):
        return False

    # Check each label of the domain
    labels = host.split(".")
    if len(labels) < 2:
        return False

    for label in labels:
        if not label:  # Empty label (consecutive dots or leading/trailing dot)
            return False
        if len(label) > 63:
            return False
        if label.startswith("-") or label.endswith("-"):
            return False
        if not re.match(r"^[A-Za-z0-9-]+$", label):
            return False

    return True


def _looks_like_ip_address(host: str) -> bool:
    """Check if string looks like an IP address (even if invalid)."""
    # IPv4 pattern: 4 groups of 1-3 digits separated by dots
    ipv4_pattern = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
    if ipv4_pattern.match(host):
        return True

    labels = host.split(".")
    if len(labels) >= 2 and all(label.isdigit() for label in labels):
        return True

    if len(labels) == 3 and all(label.isdigit() for label in labels):
        return True

    if len(labels) == 4 and all(label.isdigit() for label in labels[:3]):
        return True

    # IPv6 pattern (basic check)
    return ":" in host


def _is_hostname(host: str) -> bool:
    """Check if string is a valid hostname (no domain)."""
    if len(host) > 63:
        return False

    if "." in host:
        return False  # Hostnames with dots should be treated as domains

    # Simple hostname validation
    if host.startswith("-") or host.endswith("-"):
        return False
    return bool(re.match(r"^[A-Za-z0-9-]+$", host))


def validate_network_cidr(cidr: str) -> None:
    """
    Validate a network CIDR notation.

    Args:
        cidr: CIDR string like "192.168.1.0/24"

    Raises:
        ValidationError: If CIDR format is invalid
    """
    if not cidr or not isinstance(cidr, str):
        raise ValidationError("CIDR cannot be empty")

    if "/" not in cidr:
        raise ValidationError(f"Invalid CIDR format: {cidr}")

    try:
        network = ipaddress.IPv4Network(cidr, strict=True)

        # Additional validation for practical WireGuard networks
        if network.prefixlen < 8 or network.prefixlen > 32:
            raise ValidationError(
                f"Network prefix length must be between 8 and 32, got {network.prefixlen}"
            )

    except ipaddress.AddressValueError as e:
        raise ValidationError(f"Invalid CIDR format: {cidr}") from e
    except ValueError as e:
        raise ValidationError(str(e)) from e


def validate_wireguard_public_key(key: str) -> None:
    """
    Validate a WireGuard public key format.

    Args:
        key: Base64 encoded public key

    Raises:
        ValidationError: If key format is invalid
    """
    if not key or not isinstance(key, str):
        raise ValidationError("Public key cannot be empty")

    allowed_lengths = {44, 45, 56}
    if len(key) not in allowed_lengths:
        raise ValidationError(
            "Public key must be 44, 45, or 56 characters, " f"got {len(key)}"
        )

    # Try base64 decoding - WireGuard keys are base64 encoded
    import base64

    # Remove any whitespace that might be present
    clean_key = key.replace(" ", "").replace("\n", "").replace("\r", "")
    try:
        base64.b64decode(clean_key, validate=True)
    except Exception as e:
        if len(clean_key) == 45 and clean_key.endswith("="):
            base64.b64decode(clean_key[:-1], validate=True)
            return
        raise ValidationError(f"Invalid base64 public key: {str(e)}") from e


def validate_dns_servers(dns: str | None) -> None:
    """
    Validate DNS server list.

    Args:
        dns: Comma-separated list of DNS servers

    Raises:
        ValidationError: If DNS server format is invalid
    """
    if not dns:
        return

    servers = [s.strip() for s in dns.split(",")]

    # Check for empty entries (consecutive commas, leading/trailing commas)
    if any(not s for s in servers):
        raise ValidationError("DNS server list cannot contain empty entries")

    # Filter out empty entries for validation
    servers = [s for s in servers if s]

    for server in servers:
        if (
            not _is_ip_address(server)
            and not _is_domain_name(server)
            and not _is_hostname(server)
        ):
            raise ValidationError(f"Invalid DNS server: {server}")


def validate_mtu(mtu: int | None) -> None:
    """
    Validate MTU value.

    Args:
        mtu: MTU value in bytes

    Raises:
        ValidationError: If MTU is invalid
    """
    if mtu is None:
        return

    if not isinstance(mtu, int):
        raise ValidationError("MTU must be an integer")

    if mtu < 576 or mtu > 9000:
        raise ValidationError(f"MTU must be between 576 and 9000 bytes, got {mtu}")


def is_private_ip(ip: str) -> bool:
    """Check if an IP address is private (RFC1918)."""
    try:
        ip_obj = ipaddress.ip_address(ip)
        return ip_obj.is_private
    except ValueError:
        return False


def is_public_ip(ip: str) -> bool:
    """Check if an IP address is public."""
    try:
        ip_obj = ipaddress.ip_address(ip)
        return (
            not ip_obj.is_private
            and not ip_obj.is_loopback
            and not ip_obj.is_link_local
        )
    except ValueError:
        return False


def validate_external_endpoint(endpoint: str, allow_private: bool = False) -> None:
    """
    Validate an external endpoint with security checks.

    Args:
        endpoint: Endpoint string in format "host:port"
        allow_private: Whether to allow private IP addresses

    Raises:
        ValidationError: If endpoint is invalid or violates security rules
    """
    host, port = validate_endpoint(endpoint)

    # Additional security validation for external endpoints
    if _is_ipv4_address(host) and not allow_private and is_private_ip(host):
        raise ValidationError(
            f"External endpoint cannot use private IP address: {host}. "
            "Use a public IP or domain name for external connectivity."
        )

    # For domain names, we could add DNS resolution validation here
    # but that would require network calls and async handling
    # For now, just validate the format


def validate_persistent_keepalive(keepalive: int | None) -> None:
    """
    Validate persistent keepalive value.

    Args:
        keepalive: Keepalive interval in seconds

    Raises:
        ValidationError: If keepalive is invalid
    """
    if keepalive is None:
        return

    if not isinstance(keepalive, int):
        raise ValidationError("Persistent keepalive must be an integer")

    if keepalive < 0 or keepalive > 86400:  # Max 24 hours
        raise ValidationError(
            f"Persistent keepalive must be between 0 and 86400 seconds, got {keepalive}"
        )


PEER_PROPERTY_KEY_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")
RESERVED_PEER_PROPERTY_KEYS = {
    "PrivateKey",
    "PublicKey",
    "AllowedIPs",
    "Endpoint",
    "PresharedKey",
}


def validate_interface_properties(properties: dict[str, object] | None) -> None:
    """Validate interface properties to ensure no line breaks in values."""
    if properties is None:
        return

    if not isinstance(properties, dict):
        raise ValidationError("Interface properties must be a JSON object")

    for key, value in properties.items():
        if not isinstance(key, str) or not key:
            raise ValidationError("Interface property keys must be non-empty strings")

        # Check if the value contains line breaks
        if isinstance(value, str):
            if "\n" in value or "\r" in value:
                raise ValidationError(
                    f"Interface property '{key}' cannot contain line breaks"
                )
        elif not isinstance(value, (int, bool)) and value is not None:
            raise ValidationError(
                f"Interface property '{key}' must be a string, integer, boolean, or null"
            )


def validate_peer_properties(properties: dict[str, object] | None) -> None:
    """Validate additional peer properties for device-to-device links."""
    if properties is None:
        return

    if not isinstance(properties, dict):
        raise ValidationError("Peer properties must be a JSON object")

    for key, value in properties.items():
        if not isinstance(key, str) or not key:
            raise ValidationError("Peer property keys must be non-empty strings")
        if not PEER_PROPERTY_KEY_PATTERN.match(key):
            raise ValidationError(f"Invalid peer property key: {key}")
        if key in RESERVED_PEER_PROPERTY_KEYS:
            raise ValidationError(
                f"Peer property key '{key}' is reserved and cannot be overridden"
            )
        if key == "PersistentKeepalive":
            if value is None:
                validate_persistent_keepalive(None)
                continue
            if isinstance(value, bool):
                raise ValidationError("PersistentKeepalive must be an integer or null")
            try:
                validate_persistent_keepalive(int(value))
            except (ValueError, TypeError) as exc:
                raise ValidationError(
                    "PersistentKeepalive must be an integer or null"
                ) from exc
            continue
        if not isinstance(value, (str, int, bool)) and value is not None:
            raise ValidationError(
                f"Peer property '{key}' must be a string, integer, boolean, or null"
            )
        # Check for line breaks in string values
        if isinstance(value, str):
            if "\n" in value or "\r" in value:
                raise ValidationError(
                    f"Peer property '{key}' cannot contain line breaks"
                )
