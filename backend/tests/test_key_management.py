"""Tests for key management utilities."""

import base64
import json

import pytest

from app.utils.encryption import decrypt_data
from app.utils.key_management import (
    decrypt_preshared_key_from_json,
    decrypt_private_key_from_json,
    derive_wireguard_public_key,
    encrypt_preshared_key,
    encrypt_private_key,
    generate_wireguard_keypair,
    generate_wireguard_preshared_key,
    generate_wireguard_private_key,
    import_wireguard_preshared_key,
    import_wireguard_private_key,
    validate_wireguard_key_import,
)


def generate_test_key_bytes(seed: str = "test") -> str:
    """Generate a valid 32-byte WireGuard key for testing."""
    # Create exactly 32 bytes using the seed, padded with nulls if needed
    seed_bytes = seed.encode()
    if len(seed_bytes) > 32:
        seed_bytes = seed_bytes[:32]
    elif len(seed_bytes) < 32:
        seed_bytes = seed_bytes + b"\x00" * (32 - len(seed_bytes))
    return base64.b64encode(seed_bytes).decode()


class TestKeyManagement:
    """Test key management encryption and decryption."""

    def test_encrypt_private_key_success(self):
        """Test successful private key encryption."""
        # Generate a valid WireGuard private key (32 bytes, base64 encoded)
        private_key = generate_test_key_bytes("private_key_test")
        master_password = "test_master_password_123"  # pragma: allowlist secret

        encrypted_json = encrypt_private_key(private_key, master_password)

        # Should return a valid JSON string
        assert isinstance(encrypted_json, str)
        encrypted_data = json.loads(encrypted_json)
        assert encrypted_data["encrypted"] is True
        assert "salt" in encrypted_data
        assert "data" in encrypted_data

    def test_encrypt_private_key_invalid_key(self):
        """Test encryption with invalid private key."""
        master_password = "test_master_password_123"  # pragma: allowlist secret

        # Empty key
        with pytest.raises(ValueError, match="WireGuard private key cannot be empty"):
            encrypt_private_key("", master_password)

        # Invalid base64
        with pytest.raises(ValueError, match="Invalid WireGuard private key"):
            encrypt_private_key("invalid_base64", master_password)

        # Wrong length (not 32 bytes when decoded)
        short_key = base64.b64encode(b"a" * 16).decode()
        with pytest.raises(ValueError, match="Invalid WireGuard private key"):
            encrypt_private_key(short_key, master_password)

    def test_encrypt_private_key_empty_password(self):
        """Test encryption with empty master password."""
        private_key = generate_test_key_bytes("test_key")

        with pytest.raises(ValueError, match="Master password cannot be empty"):
            encrypt_private_key(private_key, "")

    def test_encrypt_preshared_key_success(self):
        """Test successful preshared key encryption."""
        # Generate a valid WireGuard preshared key (32 bytes, base64 encoded)
        preshared_key = generate_test_key_bytes("preshared_key_test")
        master_password = "test_master_password_123"  # pragma: allowlist secret

        encrypted_json = encrypt_preshared_key(preshared_key, master_password)

        # Should return a valid JSON string
        assert isinstance(encrypted_json, str)
        encrypted_data = json.loads(encrypted_json)
        assert encrypted_data["encrypted"] is True
        assert "salt" in encrypted_data
        assert "data" in encrypted_data

    def test_encrypt_preshared_key_none(self):
        """Test encryption with None preshared key."""
        master_password = "test_master_password_123"  # pragma: allowlist secret

        result = encrypt_preshared_key(None, master_password)
        assert result is None

    def test_encrypt_preshared_key_empty(self):
        """Test encryption with empty preshared key."""
        master_password = "test_master_password_123"  # pragma: allowlist secret

        result = encrypt_preshared_key("", master_password)
        assert result is None

    def test_encrypt_preshared_key_invalid_key(self):
        """Test encryption with invalid preshared key."""
        master_password = "test_master_password_123"  # pragma: allowlist secret

        # Invalid base64
        with pytest.raises(ValueError, match="Invalid WireGuard preshared key"):
            encrypt_preshared_key("invalid_base64", master_password)

        # Wrong length (not 32 bytes when decoded)
        short_key = base64.b64encode(b"b" * 16).decode()
        with pytest.raises(ValueError, match="Invalid WireGuard preshared key"):
            encrypt_preshared_key(short_key, master_password)

    def test_decrypt_private_key_success(self):
        """Test successful private key decryption."""
        original_key = generate_test_key_bytes("private_key_decrypt_test")
        master_password = "test_master_password_123"  # pragma: allowlist secret

        # Encrypt the key
        encrypted_json = encrypt_private_key(original_key, master_password)

        # Decrypt the key
        decrypted_key = decrypt_private_key_from_json(encrypted_json, master_password)

        assert decrypted_key == original_key

    def test_decrypt_private_key_wrong_password(self):
        """Test decryption with wrong master password."""
        original_key = generate_test_key_bytes("private_key_wrong_pass_test")
        master_password = "test_master_password_123"  # pragma: allowlist secret
        wrong_password = "wrong_password"  # pragma: allowlist secret

        # Encrypt the key
        encrypted_json = encrypt_private_key(original_key, master_password)

        # Try to decrypt with wrong password
        with pytest.raises(ValueError, match="Invalid master password"):
            decrypt_private_key_from_json(encrypted_json, wrong_password)

    def test_decrypt_private_key_invalid_json(self):
        """Test decryption with invalid JSON."""
        master_password = "test_master_password_123"  # pragma: allowlist secret

        # Invalid JSON
        with pytest.raises(ValueError, match="Invalid encrypted private key format"):
            decrypt_private_key_from_json("not_valid_json", master_password)

        # JSON without required fields
        incomplete_json = json.dumps({"encrypted": True})
        with pytest.raises(ValueError, match="Invalid master password"):
            decrypt_private_key_from_json(incomplete_json, master_password)

    def test_decrypt_private_key_empty_inputs(self):
        """Test decryption with empty inputs."""
        master_password = "test_master_password_123"  # pragma: allowlist secret

        # Empty encrypted data
        with pytest.raises(ValueError, match="Encrypted private key cannot be empty"):
            decrypt_private_key_from_json("", master_password)

        # Empty master password
        with pytest.raises(ValueError, match="Master password cannot be empty"):
            decrypt_private_key_from_json('{"encrypted": true}', "")

    def test_decrypt_preshared_key_success(self):
        """Test successful preshared key decryption."""
        original_key = generate_test_key_bytes("preshared_key_decrypt_test")
        master_password = "test_master_password_123"  # pragma: allowlist secret

        # Encrypt the key
        encrypted_json = encrypt_preshared_key(original_key, master_password)

        # Decrypt the key
        decrypted_key = decrypt_preshared_key_from_json(encrypted_json, master_password)

        assert decrypted_key == original_key

    def test_decrypt_preshared_key_none(self):
        """Test decryption with None preshared key."""
        master_password = "test_master_password_123"  # pragma: allowlist secret

        result = decrypt_preshared_key_from_json(None, master_password)
        assert result is None

        result = decrypt_preshared_key_from_json("", master_password)
        assert result is None

    def test_decrypt_preshared_key_wrong_password(self):
        """Test preshared key decryption with wrong master password."""
        original_key = generate_test_key_bytes("preshared_key_wrong_pass_test")
        master_password = "test_master_password_123"  # pragma: allowlist secret
        wrong_password = "wrong_password"  # pragma: allowlist secret

        # Encrypt the key
        encrypted_json = encrypt_preshared_key(original_key, master_password)

        # Try to decrypt with wrong password
        with pytest.raises(ValueError, match="Invalid master password"):
            decrypt_preshared_key_from_json(encrypted_json, wrong_password)

    def test_round_trip_with_real_wireguard_keys(self):
        """Test encryption/decryption with realistic WireGuard keys."""
        # Real WireGuard private key (32 bytes, base64 encoded)
        real_private_key = (
            "4OJOV6n8nYcBl7A9AaKN7/BF6GqzDYO8wl+IiDez5Ws="  # pragma: allowlist secret
        )
        master_password = (
            "secure_master_password_for_production"  # pragma: allowlist secret
        )

        # Test private key
        encrypted_private = encrypt_private_key(real_private_key, master_password)
        decrypted_private = decrypt_private_key_from_json(
            encrypted_private, master_password
        )
        assert decrypted_private == real_private_key

        # Test preshared key
        real_preshared_key = (
            "8Kqe3WJ4vEY8qAHQjPqgrBEIfaOm+n9IOLwpHLOx0HM="  # pragma: allowlist secret
        )
        encrypted_preshared = encrypt_preshared_key(real_preshared_key, master_password)
        decrypted_preshared = decrypt_preshared_key_from_json(
            encrypted_preshared, master_password
        )
        assert decrypted_preshared == real_preshared_key

    def test_encryption_output_determinism(self):
        """Test that encryption produces different output each time (due to salt)."""
        private_key = generate_test_key_bytes("determinism_test_key")
        master_password = "test_master_password_123"  # pragma: allowlist secret

        # Encrypt twice
        encrypted1 = encrypt_private_key(private_key, master_password)
        encrypted2 = encrypt_private_key(private_key, master_password)

        # Should be different due to random salt
        assert encrypted1 != encrypted2

        # But both should decrypt to the same value
        decrypted1 = decrypt_private_key_from_json(encrypted1, master_password)
        decrypted2 = decrypt_private_key_from_json(encrypted2, master_password)
        assert decrypted1 == decrypted2 == private_key

    def test_compatibility_with_encryption_utils(self):
        """Test that key management is compatible with encryption utilities."""
        private_key = generate_test_key_bytes("compatibility_test_key")
        master_password = "test_master_password_123"  # pragma: allowlist secret

        # Encrypt using key management
        encrypted_json = encrypt_private_key(private_key, master_password)
        encrypted_data = json.loads(encrypted_json)

        # Decrypt using encryption utilities directly
        decrypted_direct = decrypt_data(encrypted_data, master_password)

        # Should match original
        assert decrypted_direct == private_key


class TestKeyGenerationAndImport:
    """Test key generation and import functionality."""

    def test_generate_wireguard_private_key(self):
        """Test WireGuard private key generation."""
        private_key = generate_wireguard_private_key()

        # Should be a valid base64-encoded 32-byte key
        assert isinstance(private_key, str)
        assert len(private_key) == 44  # 32 bytes base64 encoded

        # Should be valid base64
        decoded = base64.b64decode(private_key)
        assert len(decoded) == 32

        # Should generate different keys each time
        private_key_2 = generate_wireguard_private_key()
        assert private_key != private_key_2

    def test_generate_wireguard_preshared_key(self):
        """Test WireGuard preshared key generation."""
        preshared_key = generate_wireguard_preshared_key()

        # Should be a valid base64-encoded 32-byte key
        assert isinstance(preshared_key, str)
        assert len(preshared_key) == 44  # 32 bytes base64 encoded

        # Should be valid base64
        decoded = base64.b64decode(preshared_key)
        assert len(decoded) == 32

        # Should generate different keys each time
        preshared_key_2 = generate_wireguard_preshared_key()
        assert preshared_key != preshared_key_2

    def test_generate_wireguard_keypair(self):
        """Test WireGuard key pair generation."""
        private_key, public_key = generate_wireguard_keypair()

        # Both should be valid base64-encoded keys
        assert isinstance(private_key, str)
        assert isinstance(public_key, str)
        assert len(private_key) == 44  # 32 bytes base64 encoded
        assert len(public_key) == 44  # 32 bytes base64 encoded

        # Should be valid base64
        decoded_private = base64.b64decode(private_key)
        decoded_public = base64.b64decode(public_key)
        assert len(decoded_private) == 32
        assert len(decoded_public) == 32

        # Private and public keys should be different
        assert private_key != public_key

        # Should generate different key pairs each time
        private_key_2, public_key_2 = generate_wireguard_keypair()
        assert private_key != private_key_2
        assert public_key != public_key_2

    def test_derive_wireguard_public_key(self):
        """Test public key derivation from private key."""
        # Generate a known key pair
        private_key, expected_public_key = generate_wireguard_keypair()

        # Derive public key from private key
        derived_public_key = derive_wireguard_public_key(private_key)

        # Should match the expected public key
        assert derived_public_key == expected_public_key

    def test_derive_public_key_invalid_private_key(self):
        """Test public key derivation with invalid private key."""
        with pytest.raises(ValueError, match="Invalid WireGuard private key"):
            derive_wireguard_public_key("invalid_key")

        with pytest.raises(ValueError, match="WireGuard private key cannot be empty"):
            derive_wireguard_public_key("")

        with pytest.raises(ValueError, match="Invalid WireGuard private key"):
            derive_wireguard_public_key(base64.b64encode(b"short").decode())

    def test_validate_wireguard_key_import_valid(self):
        """Test key import validation with valid keys."""
        # Valid generated key
        valid_key = generate_test_key_bytes("test_validation")
        normalized = validate_wireguard_key_import(valid_key, "private key")
        assert normalized == valid_key

        # Valid key with whitespace
        key_with_whitespace = f"  {valid_key}  \n"
        normalized = validate_wireguard_key_import(key_with_whitespace, "private key")
        assert normalized == valid_key

    def test_validate_wireguard_key_import_invalid(self):
        """Test key import validation with invalid keys."""
        with pytest.raises(ValueError, match="WireGuard private key cannot be empty"):
            validate_wireguard_key_import("", "private key")

        with pytest.raises(ValueError, match="WireGuard private key cannot be empty"):
            validate_wireguard_key_import(None, "private key")

        with pytest.raises(ValueError, match="Invalid WireGuard private key"):
            validate_wireguard_key_import("invalid", "private key")

    def test_validate_wireguard_key_import_test_keys(self):
        """Test that common test keys are rejected."""
        test_keys = [
            "YFWzaPiarJ8vX0Y1jVx0t9qR8kTmOSOKiqC1nNFH5Gc=",  # pragma: allowlist secret
            "4O541ed0L7fUm7UK+WtvysUJJQhEctVgm9Vw6tMfXEQ=",  # pragma: allowlist secret
            "gHyqsdO9bkFHP1cZjJW0YZLtfcCgCAVqsKklV8ASsnU=",  # pragma: allowlist secret
        ]

        for test_key in test_keys:
            with pytest.raises(
                ValueError,
                match=r"appears to be a test/example key and cannot be used in production",
            ):
                validate_wireguard_key_import(test_key, "private key")

    def test_validate_wireguard_key_import_all_zeros(self):
        """Test that all-zero private keys are rejected."""
        all_zeros_key = base64.b64encode(b"\x00" * 32).decode()

        with pytest.raises(
            ValueError, match="WireGuard private key cannot be all zeros"
        ):
            validate_wireguard_key_import(all_zeros_key, "private key")

    def test_import_wireguard_private_key_success(self):
        """Test successful private key import and encryption."""
        master_password = "test_master_password_123"  # pragma: allowlist secret
        valid_key = generate_test_key_bytes("import_test")

        encrypted_json = import_wireguard_private_key(valid_key, master_password)

        # Should return valid JSON encryption format
        assert isinstance(encrypted_json, str)
        encrypted_data = json.loads(encrypted_json)
        assert encrypted_data["encrypted"] is True
        assert "salt" in encrypted_data
        assert "data" in encrypted_data

        # Should be able to decrypt back to original
        decrypted = decrypt_private_key_from_json(encrypted_json, master_password)
        assert decrypted == valid_key

    def test_import_wireguard_preshared_key_success(self):
        """Test successful preshared key import and encryption."""
        master_password = "test_master_password_123"  # pragma: allowlist secret
        valid_key = generate_test_key_bytes("import_psk_test")

        encrypted_json = import_wireguard_preshared_key(valid_key, master_password)

        # Should return valid JSON encryption format
        assert isinstance(encrypted_json, str)
        encrypted_data = json.loads(encrypted_json)
        assert encrypted_data["encrypted"] is True
        assert "salt" in encrypted_data
        assert "data" in encrypted_data

        # Should be able to decrypt back to original
        decrypted = decrypt_preshared_key_from_json(encrypted_json, master_password)
        assert decrypted == valid_key

    def test_import_wireguard_preshared_key_none(self):
        """Test importing None preshared key."""
        master_password = "test_master_password_123"  # pragma: allowlist secret

        result = import_wireguard_preshared_key(None, master_password)
        assert result is None

    def test_import_wireguard_private_key_invalid(self):
        """Test private key import with invalid key."""
        master_password = "test_master_password_123"  # pragma: allowlist secret

        with pytest.raises(ValueError, match="WireGuard private key cannot be empty"):
            import_wireguard_private_key("", master_password)

        with pytest.raises(ValueError, match="appears to be a test/example key"):
            import_wireguard_private_key(
                "YFWzaPiarJ8vX0Y1jVx0t9qR8kTmOSOKiqC1nNFH5Gc=",  # pragma: allowlist secret
                master_password,
            )

    def test_import_wireguard_preshared_key_invalid(self):
        """Test preshared key import with invalid key."""
        master_password = "test_master_password_123"  # pragma: allowlist secret

        with pytest.raises(ValueError, match="WireGuard preshared key cannot be empty"):
            import_wireguard_preshared_key("", master_password)

        with pytest.raises(ValueError, match="appears to be a test/example key"):
            import_wireguard_preshared_key(
                "YFWzaPiarJ8vX0Y1jVx0t9qR8kTmOSOKiqC1nNFH5Gc=",  # pragma: allowlist secret
                master_password,
            )


class TestEdgeCaseCoverage:
    """Tests for edge cases to achieve 100% coverage."""

    def test_decrypt_private_key_invalid_json(self):
        """Test decrypt_private_key_from_json with invalid JSON."""
        master_password = "test_master_password_123"  # pragma: allowlist secret

        with pytest.raises(ValueError, match="Invalid encrypted private key format"):
            decrypt_private_key_from_json("invalid json{", master_password)

    def test_decrypt_private_key_decryption_failure(self):
        """Test decrypt_private_key_from_json with corrupted data."""
        master_password = "test_master_password_123"  # pragma: allowlist secret

        # Create valid JSON structure but with corrupted data
        corrupted_json = json.dumps(
            {
                "salt": "invalid_salt",
                "nonce": "invalid_nonce",
                "ciphertext": "invalid_data",
                "tag": "invalid_tag",
            }
        )

        with pytest.raises(ValueError, match="Data is not encrypted"):
            decrypt_private_key_from_json(corrupted_json, master_password)

    def test_decrypt_preshared_key_invalid_json(self):
        """Test decrypt_preshared_key_from_json with invalid JSON."""
        master_password = "test_master_password_123"  # pragma: allowlist secret

        with pytest.raises(ValueError, match="Invalid encrypted preshared key format"):
            decrypt_preshared_key_from_json("invalid json{", master_password)

    def test_decrypt_preshared_key_decryption_failure(self):
        """Test decrypt_preshared_key_from_json with corrupted data."""
        master_password = "test_master_password_123"  # pragma: allowlist secret

        # Create valid JSON structure but with corrupted data
        corrupted_json = json.dumps(
            {
                "salt": "invalid_salt",
                "nonce": "invalid_nonce",
                "ciphertext": "invalid_data",
                "tag": "invalid_tag",
            }
        )

        with pytest.raises(ValueError, match="Data is not encrypted"):
            decrypt_preshared_key_from_json(corrupted_json, master_password)

    def test_derive_public_key_invalid_key_format(self):
        """Test derive_wireguard_public_key with invalid key format."""
        # Test with completely invalid key
        with pytest.raises(ValueError, match="must be valid base64"):
            derive_wireguard_public_key("invalid_key_format_not_base64")

        # Test with wrong length base64 string
        with pytest.raises(ValueError, match="must be valid base64"):
            derive_wireguard_public_key(base64.b64encode(b"short").decode())

    def test_validate_key_import_non_string_input(self):
        """Test validate_wireguard_key_import with non-string input."""
        with pytest.raises(AttributeError):
            validate_wireguard_key_import(123, "private key")  # Integer input

        with pytest.raises(ValueError, match="cannot be empty"):
            validate_wireguard_key_import(None, "private key")  # None input

    def test_validate_key_import_all_zeros_key(self):
        """Test validate_wireguard_key_import with all-zeros private key."""
        all_zeros_key = base64.b64encode(b"\x00" * 32).decode()

        with pytest.raises(
            ValueError, match="WireGuard private key cannot be all zeros"
        ):
            validate_wireguard_key_import(all_zeros_key, "private key")
