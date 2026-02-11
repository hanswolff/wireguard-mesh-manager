"""API key utilities."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime

try:
    import bcrypt
except ImportError:
    bcrypt = None

# Hash format identifiers
BCRYPT_HASH_PREFIX = "$2b$"
SHA256_HASH_LENGTH = 64


class APIKeyNotFoundError(ValueError):
    """Exception raised when API key is not found."""

    def __init__(self, api_key_id: str) -> None:
        super().__init__(f"API key with ID '{api_key_id}' not found")
        self.api_key_id = api_key_id


class DeviceNotFoundError(ValueError):
    """Exception raised when device is not found."""

    def __init__(self, device_id: str) -> None:
        super().__init__(f"Device with ID '{device_id}' not found")
        self.device_id = device_id


def generate_api_key() -> tuple[str, str]:
    """Generate a new API key and return both the value and hash.

    Returns:
        tuple: (api_key_value, api_key_hash)

    Raises:
        RuntimeError: If bcrypt is not available
    """
    if bcrypt is None:
        raise RuntimeError(
            "bcrypt is required for secure API key hashing. "
            "Install it with: pip install bcrypt"
        )

    key_value = secrets.token_urlsafe(32)
    key_bytes = key_value.encode("utf-8")
    salt = bcrypt.gensalt()
    key_hash = bcrypt.hashpw(key_bytes, salt).decode("utf-8")

    return key_value, key_hash


def compute_api_key_fingerprint(key_value: str) -> str:
    """Compute a deterministic fingerprint for API key lookup."""
    if not key_value:
        raise ValueError("API key value cannot be empty")
    return hashlib.sha256(key_value.encode()).hexdigest()


def verify_api_key(key_value: str, key_hash: str) -> bool:
    """Verify an API key against its hash using constant-time comparison.

    Args:
        key_value: The plain text API key to verify
        key_hash: The stored hash to verify against

    Returns:
        bool: True if the key matches the hash, False otherwise

    Raises:
        RuntimeError: If bcrypt is not available
    """
    if bcrypt is None:
        raise RuntimeError(
            "bcrypt is required for secure API key verification. "
            "Install it with: pip install bcrypt"
        )

    return _verify_bcrypt_key(key_value, key_hash)


def _verify_bcrypt_key(key_value: str, key_hash: str) -> bool:
    """Verify API key using bcrypt."""
    try:
        key_bytes = key_value.encode("utf-8")
        stored_hash_bytes = key_hash.encode("utf-8")
        return bcrypt.checkpw(key_bytes, stored_hash_bytes)
    except (ValueError, TypeError, UnicodeEncodeError):
        # Handle specific bcrypt errors without catching everything
        return False


def _verify_sha256_key(key_value: str, key_hash: str) -> bool:
    """Verify API key using SHA-256 (legacy fallback)."""
    computed_hash = hashlib.sha256(key_value.encode()).hexdigest()
    return hmac.compare_digest(computed_hash, key_hash)


def parse_expiry_timestamp(timestamp: str | None) -> datetime | None:
    """Parse expiry timestamp from string, ensuring it's in the future."""
    if not timestamp:
        return None

    try:
        expiry_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if expiry_time <= datetime.now(UTC):
            raise ValueError("Expiry time must be in the future")
        return expiry_time
    except ValueError as e:
        if "must be in the future" in str(e):
            raise
        raise ValueError("Invalid expiry timestamp format. Use ISO 8601 format.") from e


def validate_ip_ranges(ip_ranges: str) -> str:
    """Validate IP ranges format."""
    if not ip_ranges:
        raise ValueError("allowed_ip_ranges is required")

    import ipaddress

    ranges = [r.strip() for r in ip_ranges.split(",")]
    for range_str in ranges:
        if not range_str:
            continue
        try:
            if "/" in range_str:
                ipaddress.ip_network(range_str, strict=False)
            else:
                ipaddress.ip_address(range_str)
        except ValueError as e:
            raise ValueError(f"Invalid IP range '{range_str}': {e}") from e
    return ip_ranges
