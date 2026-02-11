"""Tests for master password cache service."""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.services.master_password import MasterPasswordCache, master_password_cache


class TestMasterPasswordCache:
    """Test cases for MasterPasswordCache."""

    def setup_method(self) -> None:
        """Set up test case with fresh cache instance."""
        # Get a fresh instance for each test
        self.cache = MasterPasswordCache()
        # Ensure it starts locked
        self.cache.lock()

    def test_singleton_pattern(self) -> None:
        """Test that the cache follows singleton pattern."""
        cache1 = MasterPasswordCache()
        cache2 = MasterPasswordCache()
        assert cache1 is cache2

    def test_initial_state(self) -> None:
        """Test that cache starts in locked state."""
        assert self.cache.is_unlocked is False
        assert self.cache.password_id is None
        assert self.cache.expires_at is None
        assert self.cache.idle_expires_at is None
        assert self.cache.access_count == 0
        assert self.cache.last_access is None

    def test_unlock_with_valid_password(self) -> None:
        """Test successful unlock with valid password."""
        password = "test_password_123"  # pragma: allowlist secret

        result = self.cache.unlock(password)

        assert result is True
        assert self.cache.is_unlocked is True
        assert self.cache.password_id is not None
        assert len(self.cache.password_id) == 16
        assert self.cache.expires_at is not None
        assert self.cache.idle_expires_at is not None
        assert self.cache.expires_at > datetime.now(UTC)
        assert self.cache.idle_expires_at > datetime.now(UTC)

    def test_unlock_with_empty_password(self) -> None:
        """Test that unlock fails with empty password."""
        with pytest.raises(ValueError, match="Master password cannot be empty"):
            self.cache.unlock("")

    def test_unlock_with_none_password(self) -> None:
        """Test that unlock fails with None password."""
        with pytest.raises(ValueError, match="Master password cannot be empty"):
            self.cache.unlock(None)  # type: ignore

    def test_get_master_password_when_locked(self) -> None:
        """Test that getting password fails when locked."""
        with pytest.raises(
            ValueError, match="Master password cache is locked or expired"
        ):
            self.cache.get_master_password()

    def test_get_master_password_when_unlocked(self) -> None:
        """Test getting password when unlocked."""
        password = "test_password_123"  # pragma: allowlist secret
        self.cache.unlock(password)

        retrieved_password = self.cache.get_master_password()

        assert retrieved_password == password
        assert self.cache.access_count == 1
        assert self.cache.last_access is not None

    def test_verify_password_when_unlocked(self) -> None:
        """Test password verification when unlocked."""
        password = "test_password_123"  # pragma: allowlist secret
        self.cache.unlock(password)

        # Correct password should verify
        assert self.cache.verify_password(password) is True

        # Incorrect password should not verify
        assert self.cache.verify_password("wrong_password") is False

    def test_verify_password_when_locked(self) -> None:
        """Test password verification when locked."""
        assert self.cache.verify_password("any_password") is False

    def test_manual_lock(self) -> None:
        """Test manual locking of cache."""
        password = "test_password_123"  # pragma: allowlist secret
        self.cache.unlock(password)

        # Verify unlocked
        assert self.cache.is_unlocked is True

        # Lock manually
        self.cache.lock()

        # Verify locked
        assert self.cache.is_unlocked is False
        assert self.cache.password_id is None
        assert self.cache.expires_at is None

    def test_expiration(self) -> None:
        """Test that cache expires after TTL."""
        password = "test_password_123"  # pragma: allowlist secret

        # Unlock with very short TTL
        self.cache.unlock(password, ttl_hours=0.001)  # ~3.6 seconds

        # Should be unlocked initially
        assert self.cache.is_unlocked is True

        # Manually set expires_at to the past to simulate expiration
        past_time = datetime.now(UTC) - timedelta(seconds=1)
        self.cache._expires_at = past_time

        # Should be locked after checking is_unlocked property
        assert self.cache.is_unlocked is False

    def test_extend_ttl(self) -> None:
        """Test extending TTL of unlocked cache."""
        password = "test_password_123"  # pragma: allowlist secret
        self.cache.unlock(password, ttl_hours=1.0)

        original_expires_at = self.cache.expires_at
        assert original_expires_at is not None  # Should not be None after unlock

        # Extend TTL
        result = self.cache.extend_ttl(additional_hours=2.0)

        assert result is True
        assert self.cache.expires_at is not None
        assert self.cache.expires_at > original_expires_at

    def test_extend_ttl_when_locked(self) -> None:
        """Test extending TTL when cache is locked."""
        result = self.cache.extend_ttl(additional_hours=1.0)
        assert result is False

    def test_extend_ttl_invalid_hours(self) -> None:
        """Test extending TTL with invalid hours."""
        password = "test_password_123"  # pragma: allowlist secret
        self.cache.unlock(password)

        with pytest.raises(ValueError, match="Additional hours must be positive"):
            self.cache.extend_ttl(additional_hours=0.0)

    def test_refresh_access(self) -> None:
        """Test refreshing access time."""
        password = "test_password_123"  # pragma: allowlist secret
        self.cache.unlock(password)

        # Access once to set initial last_access time
        self.cache.get_master_password()
        original_access_count = self.cache.access_count
        original_last_access = self.cache.last_access
        assert original_last_access is not None  # Should not be None after access

        # Wait a bit to ensure time difference
        time.sleep(0.01)

        # Refresh access
        result = self.cache.refresh_access()

        assert result is True
        assert (
            self.cache.access_count == original_access_count
        )  # Count shouldn't change
        assert self.cache.last_access is not None
        assert self.cache.last_access > original_last_access

    def test_refresh_access_when_locked(self) -> None:
        """Test refreshing access when locked."""
        result = self.cache.refresh_access()
        assert result is False

    def test_get_status(self) -> None:
        """Test getting cache status."""
        password = "test_password_123"  # pragma: allowlist secret

        # Status when locked
        status = self.cache.get_status()
        assert status["is_unlocked"] is False
        assert status["password_id"] is None
        assert status["expires_at"] is None
        assert status["idle_expires_at"] is None
        assert status["access_count"] == 0
        assert status["last_access"] is None
        assert status["ttl_seconds"] == 0
        assert status["idle_ttl_seconds"] == 0

        # Unlock and get status
        self.cache.unlock(password, ttl_hours=2.0)
        self.cache.get_master_password()  # Increment access count

        status = self.cache.get_status()
        assert status["is_unlocked"] is True
        assert status["password_id"] is not None
        assert status["expires_at"] is not None
        assert status["idle_expires_at"] is not None
        assert status["access_count"] == 1
        assert status["last_access"] is not None
        assert status["ttl_seconds"] > 0
        assert status["idle_ttl_seconds"] > 0

    def test_re_unlock_with_different_password(self) -> None:
        """Test unlocking with different password."""
        password1 = "test_password_123"  # pragma: allowlist secret
        password2 = "different_password_456"  # pragma: allowlist secret

        # Unlock with first password
        self.cache.unlock(password1)
        assert self.cache.verify_password(password1) is True
        assert self.cache.verify_password(password2) is False
        original_password_id = self.cache.password_id

        # Unlock with different password
        self.cache.unlock(password2)
        assert self.cache.verify_password(password1) is False
        assert self.cache.verify_password(password2) is True
        # Password ID should change (since we use random salt)
        assert self.cache.password_id != original_password_id

    def test_multiple_access_counting(self) -> None:
        """Test that access counter increments correctly."""
        password = "test_password_123"  # pragma: allowlist secret
        self.cache.unlock(password)

        # Access multiple times
        for i in range(5):
            retrieved_password = self.cache.get_master_password()
            assert retrieved_password == password
            assert self.cache.access_count == i + 1

    @patch("app.services.master_password.logger")
    def test_logging_on_unlock(self, mock_logger: MagicMock) -> None:
        """Test that unlock operation is logged."""
        password = "test_password_123"  # pragma: allowlist secret
        self.cache.unlock(password)

        # Check that logger.info was called
        mock_logger.info.assert_called()

        # Find the unlock call
        unlock_calls = [
            call
            for call in mock_logger.info.call_args_list
            if "Master password cache unlocked" in str(call)
        ]
        assert len(unlock_calls) == 1

    @patch("app.services.master_password.logger")
    def test_logging_on_lock(self, mock_logger: MagicMock) -> None:
        """Test that lock operation is logged."""
        password = "test_password_123"  # pragma: allowlist secret
        self.cache.unlock(password)

        # Clear previous calls
        mock_logger.info.reset_mock()

        # Lock
        self.cache.lock()

        # Check that logger.info was called for lock
        lock_calls = [
            call
            for call in mock_logger.info.call_args_list
            if "Master password cache manually locked" in str(call)
        ]
        assert len(lock_calls) == 1


class TestGlobalMasterPasswordCache:
    """Test cases for the global master_password_cache instance."""

    def test_global_instance_exists(self) -> None:
        """Test that the global instance exists and is a MasterPasswordCache."""
        assert master_password_cache is not None
        assert isinstance(master_password_cache, MasterPasswordCache)

    def test_global_instance_is_singleton(self) -> None:
        """Test that importing the global instance returns the same object."""
        from app.services.master_password import master_password_cache as imported_cache

        assert master_password_cache is imported_cache
