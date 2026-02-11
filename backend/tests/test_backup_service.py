"""Tests for backup service functionality."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.backup import BackupRecord, BackupService
from app.utils.encryption import decrypt_data, encrypt_data


class TestBackupService:
    """Test cases for BackupService."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock()

    @pytest.fixture
    def backup_service(self, mock_db):
        """Create a backup service instance."""
        return BackupService(mock_db)

    def test_generate_password(self, backup_service):
        """Test password generation."""
        password = backup_service.generate_password()

        assert len(password) == 32
        assert any(c.islower() for c in password)
        assert any(c.isupper() for c in password)
        assert any(c.isdigit() for c in password)
        assert any(c in "!@#$%^&*" for c in password)

    def test_generate_password_custom_length(self, backup_service):
        """Test password generation with custom length."""
        password = backup_service.generate_password(16)

        assert len(password) == 16

    @pytest.mark.asyncio
    async def test_create_backup_record_unencrypted(self, backup_service, mock_db):
        """Test creating backup record for unencrypted data."""
        test_data = {"networks": [{"name": "test-net", "locations": [], "devices": []}]}

        # Mock the database operations
        mock_audit = MagicMock()
        mock_audit.id = "test-id"
        mock_audit.occurred_at = datetime.now(UTC)
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock(return_value=None)

        # Mock the AuditEvent constructor to return our mock
        with patch("app.services.backup.AuditEvent") as mock_audit_class:
            mock_audit_class.return_value = mock_audit

            record = await backup_service.create_backup_record(
                description="Test backup",
                exported_by="test-user",
                encrypted=False,
                data=test_data,
            )

            assert isinstance(record, BackupRecord)
            assert record.id == "test-id"
            assert record.description == "Test backup"
            assert record.exported_by == "test-user"
            assert record.encrypted is False
            mock_db.add.assert_called_once()
            mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_backup_record_encrypted(self, backup_service, mock_db):
        """Test creating backup record for encrypted data."""
        test_data = {"encrypted": True, "version": "1.0"}

        # Mock the database operations
        mock_audit = MagicMock()
        mock_audit.id = "test-id"
        mock_audit.occurred_at = datetime.now(UTC)
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock(return_value=None)

        # Mock the AuditEvent constructor to return our mock
        with patch("app.services.backup.AuditEvent") as mock_audit_class:
            mock_audit_class.return_value = mock_audit

            record = await backup_service.create_backup_record(
                description=None, exported_by="api", encrypted=True, data=test_data
            )

            assert isinstance(record, BackupRecord)
            assert record.description is None
            assert record.exported_by == "api"
            assert record.encrypted is True

    @pytest.mark.asyncio
    async def test_create_restore_record(self, backup_service, mock_db):
        """Test creating restore record."""
        # Mock the database operations
        mock_audit = MagicMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock(return_value=None)

        # Mock the AuditEvent constructor to return our mock
        with patch("app.services.backup.AuditEvent") as mock_audit_class:
            mock_audit_class.return_value = mock_audit

            await backup_service.create_restore_record(
                networks_restored=5,
                networks_updated=2,
                locations_created=10,
                devices_created=25,
                errors=["Test error"],
            )

            mock_db.add.assert_called_once()
            mock_db.flush.assert_called_once()


class TestEncryption:
    """Test cases for encryption utilities."""

    def test_encrypt_decrypt_data(self):
        """Test basic encryption and decryption."""
        test_data = '{"test": "data"}'
        password = "test-password"

        encrypted = encrypt_data(test_data, password)

        assert encrypted["encrypted"] is True
        assert encrypted["version"] == "1.1"
        assert "salt" in encrypted
        assert encrypted["kdf"]["iterations"] == 480_000
        assert encrypted["kdf"]["name"] == "pbkdf2"
        assert encrypted["kdf"]["digest"] == "sha256"
        assert encrypted["cipher"] == {"name": "fernet"}
        assert "data" in encrypted

        decrypted = decrypt_data(encrypted, password)
        assert decrypted == test_data

    def test_decrypt_unencrypted_data_fails(self):
        """Test that decrypting unencrypted data fails."""
        unencrypted_data = {"test": "data"}
        password = "test-password"

        with pytest.raises(ValueError, match="Data is not encrypted"):
            decrypt_data(unencrypted_data, password)

    def test_decrypt_with_wrong_password_fails(self):
        """Test that decrypting with wrong password fails."""
        test_data = '{"test": "data"}'
        password = "correct-password"
        wrong_password = "wrong-password"

        encrypted = encrypt_data(test_data, password)

        with pytest.raises(ValueError, match="Failed to decrypt data"):
            decrypt_data(encrypted, wrong_password)
