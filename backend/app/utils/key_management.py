"""Key management utilities for encrypting and decrypting WireGuard keys."""

from __future__ import annotations

import base64
import json
import secrets
import subprocess

from app.utils.encryption import decrypt_data, encrypt_data

# WireGuard key constants
WIREGUARD_KEY_LENGTH = 32
DEVICE_DEK_LENGTH = 32


def _validate_wireguard_key(key: str, key_type: str) -> None:
    """Validate a WireGuard key format.

    Args:
        key: The key to validate (base64-encoded)
        key_type: Type of key for error messages ("private key" or "preshared key")

    Raises:
        ValueError: If key format is invalid
    """
    if not key:
        raise ValueError(f"WireGuard {key_type} cannot be empty")

    try:
        decoded = base64.b64decode(key)
        if len(decoded) != WIREGUARD_KEY_LENGTH:
            raise ValueError(
                f"Invalid WireGuard {key_type}: must be {WIREGUARD_KEY_LENGTH} bytes when decoded"
            )
    except (ValueError, TypeError):
        raise ValueError(
            f"Invalid WireGuard {key_type}: must be valid base64"
        ) from None


def _validate_master_password(master_password: str) -> None:
    """Validate master password is not empty.

    Args:
        master_password: Master password to validate

    Raises:
        ValueError: If master password is empty
    """
    if not master_password:
        raise ValueError("Master password cannot be empty")


def encrypt_private_key(private_key: str, master_password: str) -> str:
    """Encrypt a WireGuard private key with a master password.

    Args:
        private_key: The private key to encrypt (base64-encoded)
        master_password: Master password for encryption

    Returns:
        JSON string containing the encrypted data

    Raises:
        ValueError: If inputs are invalid
    """
    _validate_wireguard_key(private_key, "private key")
    _validate_master_password(master_password)

    encrypted_data = encrypt_data(private_key, master_password)
    return json.dumps(encrypted_data)


def generate_device_dek() -> str:
    """Generate a device data-encryption key (DEK).

    Returns:
        Base64-encoded DEK
    """
    dek_bytes = secrets.token_bytes(DEVICE_DEK_LENGTH)
    return base64.b64encode(dek_bytes).decode()


def encrypt_device_dek_with_master(dek: str, master_password: str) -> str:
    """Encrypt a device DEK with the master password."""
    if not dek:
        raise ValueError("Device DEK cannot be empty")

    _validate_master_password(master_password)

    encrypted_data = encrypt_data(dek, master_password)
    return json.dumps(encrypted_data)


def encrypt_device_dek_with_api_key(dek: str, api_key: str) -> str:
    """Encrypt a device DEK with a key derived from the API key."""
    if not dek:
        raise ValueError("Device DEK cannot be empty")
    if not api_key:
        raise ValueError("API key cannot be empty")

    encrypted_data = encrypt_data(dek, api_key)
    return json.dumps(encrypted_data)


def encrypt_preshared_key(
    preshared_key: str | None, master_password: str
) -> str | None:
    """Encrypt a WireGuard preshared key with a master password.

    Args:
        preshared_key: The preshared key to encrypt (base64-encoded), or None
        master_password: Master password for encryption

    Returns:
        JSON string containing the encrypted data, or None if preshared_key is None

    Raises:
        ValueError: If inputs are invalid
    """
    if not preshared_key:
        return None

    _validate_wireguard_key(preshared_key, "preshared key")
    _validate_master_password(master_password)

    encrypted_data = encrypt_data(preshared_key, master_password)
    return json.dumps(encrypted_data)


def encrypt_preshared_key_with_dek(
    preshared_key: str | None, dek: str
) -> str | None:
    """Encrypt a WireGuard preshared key using a device DEK."""
    if not preshared_key:
        return None

    _validate_wireguard_key(preshared_key, "preshared key")
    if not dek:
        raise ValueError("Device DEK cannot be empty")

    encrypted_data = encrypt_data(preshared_key, dek)
    return json.dumps(encrypted_data)


def encrypt_private_key_with_dek(private_key: str, dek: str) -> str:
    """Encrypt a WireGuard private key using a device DEK."""
    _validate_wireguard_key(private_key, "private key")
    if not dek:
        raise ValueError("Device DEK cannot be empty")

    encrypted_data = encrypt_data(private_key, dek)
    return json.dumps(encrypted_data)


def decrypt_private_key_from_json(encrypted_json: str, master_password: str) -> str:
    """Decrypt a private key from JSON storage format.

    Args:
        encrypted_json: JSON string containing the encrypted data
        master_password: Master password for decryption

    Returns:
        Decrypted private key

    Raises:
        ValueError: If decryption fails or inputs are invalid
    """
    if not encrypted_json:
        raise ValueError("Encrypted private key cannot be empty")

    _validate_master_password(master_password)

    try:
        encrypted_data = json.loads(encrypted_json)
        return decrypt_data(encrypted_data, master_password)
    except json.JSONDecodeError as err:
        raise ValueError(
            "Invalid encrypted private key format: not valid JSON"
        ) from err
    except Exception as e:
        error_msg = str(e).lower()
        if "invalid" in error_msg or "failed to decrypt" in error_msg:
            raise ValueError(
                "Invalid master password or corrupted encrypted data"
            ) from None
        raise


def decrypt_device_dek_from_json(encrypted_json: str, password: str) -> str:
    """Decrypt a device DEK from JSON storage format."""
    if not encrypted_json:
        raise ValueError("Encrypted device DEK cannot be empty")
    if not password:
        raise ValueError("Password cannot be empty")

    try:
        encrypted_data = json.loads(encrypted_json)
        return decrypt_data(encrypted_data, password)
    except json.JSONDecodeError as err:
        raise ValueError("Invalid encrypted device DEK format: not valid JSON") from err
    except Exception as e:
        error_msg = str(e).lower()
        if "invalid" in error_msg or "failed to decrypt" in error_msg:
            raise ValueError(
                "Invalid password or corrupted encrypted data"
            ) from None
        raise


def decrypt_private_key_with_dek(encrypted_json: str, dek: str) -> str:
    """Decrypt a private key using a device DEK."""
    if not encrypted_json:
        raise ValueError("Encrypted private key cannot be empty")
    if not dek:
        raise ValueError("Device DEK cannot be empty")

    try:
        encrypted_data = json.loads(encrypted_json)
        return decrypt_data(encrypted_data, dek)
    except json.JSONDecodeError as err:
        raise ValueError(
            "Invalid encrypted private key format: not valid JSON"
        ) from err
    except Exception as e:
        error_msg = str(e).lower()
        if "invalid" in error_msg or "failed to decrypt" in error_msg:
            raise ValueError("Invalid device DEK or corrupted encrypted data") from None
        raise


def decrypt_preshared_key_from_json(
    encrypted_json: str | None, master_password: str
) -> str | None:
    """Decrypt a preshared key from JSON storage format.

    Args:
        encrypted_json: JSON string containing the encrypted data, or None
        master_password: Master password for decryption

    Returns:
        Decrypted preshared key, or None if encrypted_json is None

    Raises:
        ValueError: If decryption fails or inputs are invalid
    """
    if not encrypted_json:
        return None

    _validate_master_password(master_password)

    try:
        encrypted_data = json.loads(encrypted_json)
        return decrypt_data(encrypted_data, master_password)
    except json.JSONDecodeError as err:
        raise ValueError(
            "Invalid encrypted preshared key format: not valid JSON"
        ) from err
    except Exception as e:
        error_msg = str(e).lower()
        if "invalid" in error_msg or "failed to decrypt" in error_msg:
            raise ValueError(
                "Invalid master password or corrupted encrypted data"
            ) from None
        raise


def decrypt_preshared_key_with_dek(
    encrypted_json: str | None, dek: str
) -> str | None:
    """Decrypt a preshared key using a device DEK."""
    if not encrypted_json:
        return None

    if not dek:
        raise ValueError("Device DEK cannot be empty")

    try:
        encrypted_data = json.loads(encrypted_json)
        return decrypt_data(encrypted_data, dek)
    except json.JSONDecodeError as err:
        raise ValueError(
            "Invalid encrypted preshared key format: not valid JSON"
        ) from err
    except Exception as e:
        error_msg = str(e).lower()
        if "invalid" in error_msg or "failed to decrypt" in error_msg:
            raise ValueError("Invalid device DEK or corrupted encrypted data") from None
        raise


def generate_wireguard_private_key() -> str:
    """Generate a secure WireGuard private key.

    Returns:
        A cryptographically secure 32-byte WireGuard private key, base64-encoded

    Note:
        Generated keys are never logged to prevent accidental exposure.
    """
    # Generate 32 cryptographically secure random bytes
    key_bytes = secrets.token_bytes(WIREGUARD_KEY_LENGTH)
    return base64.b64encode(key_bytes).decode()


def derive_wireguard_public_key(private_key: str) -> str:
    """Derive a WireGuard public key from a private key.

    Args:
        private_key: The WireGuard private key (base64-encoded)

    Returns:
        The corresponding WireGuard public key (base64-encoded)

    Raises:
        ValueError: If private key format is invalid
    """
    _validate_wireguard_key(private_key, "private key")

    # Decode private key from base64
    private_key_bytes = base64.b64decode(private_key)

    # Use WireGuard's curve25519 algorithm to derive public key
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import x25519

    # Convert the private key to the proper format for X25519
    if len(private_key_bytes) != 32:
        raise ValueError("Invalid private key length for WireGuard")

    # Create X25519 private key from the bytes
    try:
        private_key_obj = x25519.X25519PrivateKey.from_private_bytes(private_key_bytes)
        public_key_obj = private_key_obj.public_key()
        public_key_bytes = public_key_obj.public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )
        return base64.b64encode(public_key_bytes).decode()
    except Exception as e:
        raise ValueError(f"Failed to derive public key: {str(e)}") from e


def generate_wireguard_keypair() -> tuple[str, str]:
    """Generate a complete WireGuard key pair.

    Returns:
        A tuple of (private_key, public_key), both base64-encoded

    Note:
        Generated keys are never logged to prevent accidental exposure.
    """
    private_key = generate_wireguard_private_key()
    public_key = derive_wireguard_public_key(private_key)
    return private_key, public_key


def generate_wireguard_preshared_key() -> str:
    """Generate a secure WireGuard preshared key.

    Returns:
        A cryptographically secure 32-byte WireGuard preshared key, base64-encoded

    Note:
        Generated keys are never logged to prevent accidental exposure.
    """
    # Generate 32 cryptographically secure random bytes
    key_bytes = secrets.token_bytes(WIREGUARD_KEY_LENGTH)
    return base64.b64encode(key_bytes).decode()


def validate_wireguard_key_import(key: str, key_type: str) -> str:
    """Validate a WireGuard key during import.

    This function provides additional validation for imported keys beyond basic format validation.
    It checks for common issues and provides better error messages.

    Args:
        key: The key to validate (base64-encoded)
        key_type: Type of key for error messages ("private key", "public key", or "preshared key")

    Returns:
        The normalized key (trimmed of whitespace)

    Raises:
        ValueError: If key format is invalid
    """
    if not key:
        raise ValueError(f"WireGuard {key_type} cannot be empty")

    # Normalize by stripping whitespace
    normalized_key = key.strip()

    # Basic format validation
    _validate_wireguard_key(normalized_key, key_type)

    # Additional validation for imported keys
    # Check for common placeholder or test keys
    common_test_keys = {
        "YFWzaPiarJ8vX0Y1jVx0t9qR8kTmOSOKiqC1nNFH5Gc=",  # pragma: allowlist secret
        "4O541ed0L7fUm7UK+WtvysUJJQhEctVgm9Vw6tMfXEQ=",  # pragma: allowlist secret
        "gHyqsdO9bkFHP1cZjJW0YZLtfcCgCAVqsKklV8ASsnU=",  # pragma: allowlist secret
    }

    if normalized_key in common_test_keys:
        raise ValueError(
            f"WireGuard {key_type} appears to be a test/example key and cannot be used in production"
        )

    # For private keys, check if they're all zeros (invalid)
    if key_type == "private key":
        try:
            decoded = base64.b64decode(normalized_key)
            if all(b == 0 for b in decoded):
                raise ValueError("WireGuard private key cannot be all zeros")
        except (ValueError, TypeError) as e:
            # Re-raise our specific ValueError, wrap other exceptions
            if "all zeros" in str(e):
                raise
            else:
                raise ValueError("Invalid WireGuard private key format") from e

    return normalized_key


def import_wireguard_private_key(key: str, master_password: str) -> str:
    """Import and encrypt a WireGuard private key with a master password."""
    validated_key = validate_wireguard_key_import(key, "private key")
    return encrypt_private_key(validated_key, master_password)


def import_wireguard_private_key_with_dek(key: str, dek: str) -> str:
    """Import and encrypt a WireGuard private key using a device DEK."""
    validated_key = validate_wireguard_key_import(key, "private key")
    return encrypt_private_key_with_dek(validated_key, dek)


def import_wireguard_preshared_key(key: str | None, master_password: str) -> str | None:
    """Import and encrypt a WireGuard preshared key.

    This function validates the key format and encrypts it for storage.

    Args:
        key: The preshared key to import (base64-encoded), or None
        master_password: Master password for encryption

    Returns:
        JSON string containing the encrypted key, or None if key is None

    Raises:
        ValueError: If key format is invalid or encryption fails
    """
    if key is None:
        return None

    # Validate and normalize the key
    validated_key = validate_wireguard_key_import(key, "preshared key")

    # Encrypt the validated key
    return encrypt_preshared_key(validated_key, master_password)


def generate_wireguard_keypair_cli() -> tuple[str, str]:
    """Generate a WireGuard key pair using WireGuard CLI tools.

    This function uses the `wg genkey` and `wg pubkey` commands to generate
    cryptographic keys in-memory without writing to disk.

    The command chain is: `wg genkey | tee privatekey | wg pubkey > publickey`
    Adapted for in-memory execution using subprocess pipes.

    Returns:
        A tuple of (private_key, public_key), both base64-encoded

    Raises:
        RuntimeError: If WireGuard tools are not installed or execution fails
        ValueError: If the generated keys are invalid
    """
    try:
        # Generate private key using wg genkey
        private_key_proc = subprocess.run(
            ["wg", "genkey"],
            capture_output=True,
            text=True,
            check=True,
        )
        private_key = private_key_proc.stdout.strip()

        if not private_key:
            raise ValueError("WireGuard genkey produced empty output")

        # Derive public key from private key using wg pubkey
        public_key_proc = subprocess.run(
            ["wg", "pubkey"],
            input=private_key,
            capture_output=True,
            text=True,
            check=True,
        )
        public_key = public_key_proc.stdout.strip()

        if not public_key:
            raise ValueError("WireGuard pubkey produced empty output")

        # Validate the generated keys
        _validate_wireguard_key(private_key, "private key")
        _validate_wireguard_key(public_key, "public key")

        return private_key, public_key

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() if e.stderr else str(e)
        raise RuntimeError(
            f"WireGuard CLI tool execution failed: {error_msg}. "
            "Ensure WireGuard tools are installed on the system."
        ) from e
    except FileNotFoundError as e:
        raise RuntimeError(
            "WireGuard CLI tools are not installed on this system. "
            "Please install WireGuard (e.g., 'apt install wireguard' on Debian/Ubuntu, "
            "'yum install wireguard-tools' on RHEL/CentOS)."
        ) from e
    except Exception as e:
        if "wg" in str(e).lower() or "command" in str(e).lower():
            raise RuntimeError(
                f"Failed to generate WireGuard keys using CLI: {str(e)}"
            ) from e
        raise
