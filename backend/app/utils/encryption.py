"""Encryption utilities for backup operations."""

from __future__ import annotations

import base64
import secrets
from typing import Any

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

DEFAULT_KDF_ITERATIONS = 480_000


def derive_key(
    password: str,
    salt: bytes,
    *,
    iterations: int = DEFAULT_KDF_ITERATIONS,
) -> bytes:
    """Derive encryption key from password using PBKDF2.

    Args:
        password: The password to derive from
        salt: The salt to use
        iterations: The number of PBKDF2 iterations to apply

    Returns:
        Derived encryption key
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


def encrypt_data(data: str, password: str) -> dict[str, Any]:
    """Encrypt JSON data with password.

    Args:
        data: JSON string to encrypt
        password: Password for encryption

    Returns:
        Dict with encrypted data and metadata needed for decryption
    """
    salt = secrets.token_bytes(16)
    key = derive_key(password, salt)
    f = Fernet(key)

    encrypted_data = f.encrypt(data.encode())

    return {
        "encrypted": True,
        "version": "1.1",
        "salt": base64.b64encode(salt).decode(),
        "kdf": {
            "name": "pbkdf2",
            "digest": "sha256",
            "iterations": DEFAULT_KDF_ITERATIONS,
            "length": 32,
            "salt": base64.b64encode(salt).decode(),
        },
        "cipher": {"name": "fernet"},
        "data": base64.b64encode(encrypted_data).decode(),
    }


def decrypt_data(encrypted_data: dict[str, Any], password: str) -> str:
    """Decrypt data that was encrypted with encrypt_data.

    Args:
        encrypted_data: The encrypted data structure
        password: Password for decryption

    Returns:
        Decrypted JSON string

    Raises:
        ValueError: If data is not encrypted or decryption fails
    """
    if not encrypted_data.get("encrypted"):
        raise ValueError("Data is not encrypted")

    try:
        kdf_params = encrypted_data.get("kdf")

        if kdf_params:
            salt_encoded = kdf_params.get("salt", "")
            iterations = kdf_params.get("iterations", DEFAULT_KDF_ITERATIONS)
        else:
            # Backwards compatibility with v1.0 backups
            salt_encoded = encrypted_data.get("salt", "")
            iterations = DEFAULT_KDF_ITERATIONS

        salt = base64.b64decode(salt_encoded.encode())

        key = derive_key(password, salt, iterations=iterations)
        f = Fernet(key)

        encrypted_content = base64.b64decode(encrypted_data["data"].encode())
        return f.decrypt(encrypted_content).decode()
    except Exception as e:
        raise ValueError(f"Failed to decrypt data: {str(e)}") from None
