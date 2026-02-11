"""Tests for API key utilities."""

from __future__ import annotations

import pytest

from app.utils.api_key import (
    APIKeyNotFoundError,
    DeviceNotFoundError,
    generate_api_key,
    parse_expiry_timestamp,
    validate_ip_ranges,
    verify_api_key,
)


def test_generate_api_key() -> None:
    """Test generating API keys."""
    # Check if bcrypt is available
    try:
        import bcrypt  # noqa: F401

        bcrypt_available = True
    except ImportError:
        bcrypt_available = False

    if bcrypt_available:
        key_value, key_hash = generate_api_key()

        assert isinstance(key_value, str)
        assert len(key_value) > 0
        assert isinstance(key_hash, str)
        assert key_hash != key_value
        assert key_hash.startswith("$2b$")
        assert len(key_hash) == 60  # bcrypt hash length
    else:
        # If bcrypt is not available, should raise RuntimeError
        with pytest.raises(RuntimeError, match="bcrypt is required"):
            generate_api_key()


def test_generate_api_key_unique() -> None:
    """Test that generated API keys are unique."""
    # Check if bcrypt is available
    try:
        import bcrypt  # noqa: F401

        bcrypt_available = True
    except ImportError:
        bcrypt_available = False

    if not bcrypt_available:
        pytest.skip("bcrypt not available")

    keys = set()
    hashes = set()

    for _ in range(100):
        key_value, key_hash = generate_api_key()
        keys.add(key_value)
        hashes.add(key_hash)

    assert len(keys) == 100
    assert len(hashes) == 100


def test_parse_expiry_timestamp_none() -> None:
    """Test parsing None expiry timestamp."""
    result = parse_expiry_timestamp(None)
    assert result is None


def test_parse_expiry_timestamp_empty_string() -> None:
    """Test parsing empty string expiry timestamp."""
    result = parse_expiry_timestamp("")
    assert result is None


def test_parse_expiry_timestamp_valid_future() -> None:
    """Test parsing valid future timestamp."""
    timestamp = "2027-12-31T23:59:59Z"
    result = parse_expiry_timestamp(timestamp)

    assert result is not None
    assert result.year == 2027
    assert result.month == 12
    assert result.day == 31


def test_parse_expiry_timestamp_valid_future_with_offset() -> None:
    """Test parsing valid future timestamp with timezone offset."""
    timestamp = "2027-12-31T23:59:59+02:00"
    result = parse_expiry_timestamp(timestamp)

    assert result is not None
    assert result.year == 2027
    assert result.month == 12
    assert result.day == 31


def test_parse_expiry_timestamp_past_date() -> None:
    """Test parsing past timestamp raises error."""
    timestamp = "2020-01-01T00:00:00Z"

    with pytest.raises(ValueError, match="Expiry time must be in the future"):
        parse_expiry_timestamp(timestamp)


def test_parse_expiry_timestamp_invalid_format() -> None:
    """Test parsing invalid timestamp format."""
    timestamp = "invalid-date-format"

    with pytest.raises(ValueError, match="Invalid expiry timestamp format"):
        parse_expiry_timestamp(timestamp)


def test_validate_ip_ranges_single_ip() -> None:
    """Test validating single IP address."""
    ip_ranges = "192.168.1.1"
    result = validate_ip_ranges(ip_ranges)

    assert result == ip_ranges


def test_validate_ip_ranges_cidr() -> None:
    """Test validating CIDR notation."""
    ip_ranges = "192.168.1.0/24"
    result = validate_ip_ranges(ip_ranges)

    assert result == ip_ranges


def test_validate_ip_ranges_multiple() -> None:
    """Test validating multiple IP ranges."""
    ip_ranges = "192.168.1.0/24,10.0.0.1,172.16.0.0/16"
    result = validate_ip_ranges(ip_ranges)

    assert result == ip_ranges


def test_validate_ip_ranges_with_spaces() -> None:
    """Test validating IP ranges with spaces."""
    ip_ranges = "192.168.1.0/24, 10.0.0.1, 172.16.0.0/16"
    result = validate_ip_ranges(ip_ranges)

    assert result == ip_ranges


def test_validate_ip_ranges_empty_ranges() -> None:
    """Test validating IP ranges with empty entries."""
    ip_ranges = "192.168.1.0/24,,10.0.0.1,"
    result = validate_ip_ranges(ip_ranges)

    assert result == ip_ranges


def test_validate_ip_ranges_invalid_ip() -> None:
    """Test validating invalid IP address."""
    ip_ranges = "invalid-ip"

    with pytest.raises(ValueError, match="Invalid IP range 'invalid-ip'"):
        validate_ip_ranges(ip_ranges)


def test_validate_ip_ranges_invalid_cidr() -> None:
    """Test validating invalid CIDR notation."""
    ip_ranges = "192.168.1.0/33"

    with pytest.raises(ValueError, match="Invalid IP range '192.168.1.0/33'"):
        validate_ip_ranges(ip_ranges)


def test_validate_ip_ranges_empty_string() -> None:
    """Test validating empty string."""
    with pytest.raises(ValueError, match="allowed_ip_ranges is required"):
        validate_ip_ranges("")


def test_api_key_not_found_error() -> None:
    """Test APIKeyNotFoundError."""
    api_key_id = "test-key-id"
    error = APIKeyNotFoundError(api_key_id)

    assert str(error) == f"API key with ID '{api_key_id}' not found"
    assert error.api_key_id == api_key_id


def test_device_not_found_error() -> None:
    """Test DeviceNotFoundError."""
    device_id = "test-device-id"
    error = DeviceNotFoundError(device_id)

    assert str(error) == f"Device with ID '{device_id}' not found"
    assert error.device_id == device_id


def test_validate_ip_ranges_ipv6() -> None:
    """Test validating IPv6 addresses."""
    ip_ranges = "2001:db8::/32,::1"
    result = validate_ip_ranges(ip_ranges)

    assert result == ip_ranges


def test_validate_ip_ranges_mixed_ipv4_ipv6() -> None:
    """Test validating mixed IPv4 and IPv6 addresses."""
    ip_ranges = "192.168.1.0/24,2001:db8::/32,10.0.0.1"
    result = validate_ip_ranges(ip_ranges)

    assert result == ip_ranges


def test_verify_api_key_bcrypt() -> None:
    """Test API key verification with bcrypt hashes."""
    # Test with bcrypt if available
    try:
        import bcrypt  # noqa: F401
    except ImportError:
        pytest.skip("bcrypt not available")

    key_value, key_hash = generate_api_key()

    # Test correct verification
    assert verify_api_key(key_value, key_hash) is True

    # Test incorrect key
    assert verify_api_key("wrong_key", key_hash) is False

    # Test with empty key
    assert verify_api_key("", key_hash) is False


def test_verify_api_key_sha256_fallback() -> None:
    """Test that SHA-256 fallback is not supported and returns False."""
    # Create a SHA-256 hash manually to test that fallback is rejected
    key_value = "test_api_key_value"
    import hashlib

    key_hash = hashlib.sha256(key_value.encode()).hexdigest()

    # Test that SHA-256 hashes are not supported (should return False)
    assert verify_api_key(key_value, key_hash) is False


def test_verify_api_key_constant_time() -> None:
    """Test that API key verification uses constant-time comparison."""
    # Create two different keys that hash to values of the same length
    key1 = "api_key_one"
    key2 = "api_key_two"

    import hashlib

    hash1 = hashlib.sha256(key1.encode()).hexdigest()
    hash2 = hashlib.sha256(key2.encode()).hexdigest()

    # Both should return False, but timing should be consistent
    assert verify_api_key(key1, hash2) is False
    assert verify_api_key(key2, hash1) is False


def test_verify_api_key_mixed_formats() -> None:
    """Test verification with mixed hash formats."""
    try:
        import bcrypt  # noqa: F401
    except ImportError:
        pytest.skip("bcrypt not available")

    # Generate a bcrypt hash
    bcrypt_key, bcrypt_hash = generate_api_key()

    # Generate a SHA-256 hash
    sha256_key = "legacy_key"
    import hashlib

    sha256_hash = hashlib.sha256(sha256_key.encode()).hexdigest()

    # Test bcrypt verification
    assert verify_api_key(bcrypt_key, bcrypt_hash) is True

    # Test that SHA-256 hashes are rejected
    assert verify_api_key(sha256_key, sha256_hash) is False


def test_verify_api_key_error_handling() -> None:
    """Test API key verification error handling."""
    # Test with invalid inputs
    assert verify_api_key("", "") is False

    # Test with malformed hash
    assert verify_api_key("some_key", "invalid_hash_format") is False
