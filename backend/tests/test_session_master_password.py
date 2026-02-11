"""Tests for session-based master password cache service."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from unittest.mock import patch

from app.services.master_password import (
    SessionMasterPasswordCache,
    get_master_password_cache,
    session_manager,
)


class TestSessionMasterPasswordCache:
    """Test cases for SessionMasterPasswordCache."""

    def setup_method(self) -> None:
        """Set up test case with fresh session cache instance."""
        self.session_id = "test-session-123"
        self.cache = SessionMasterPasswordCache(self.session_id)

    def test_initial_state(self) -> None:
        """Test that cache starts in locked state."""
        assert self.cache.is_unlocked is False
        assert self.cache.password_id is None
        assert self.cache.expires_at is None
        assert self.cache.idle_expires_at is None
        assert self.cache.access_count == 0
        assert self.cache.last_access is None
        assert self.cache.session_id == self.session_id

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

    def test_idle_timeout_expiration(self) -> None:
        """Test that cache expires after idle timeout."""
        password = "test_password_123"  # pragma: allowlist secret

        # Create a new cache with very short idle timeout for testing
        with patch(
            "app.config.settings.master_password_idle_timeout_minutes", 0.001
        ):  # ~0.06 seconds
            short_timeout_cache = SessionMasterPasswordCache("short-timeout-session")

            result = short_timeout_cache.unlock(password)
            assert result is True
            assert short_timeout_cache.is_unlocked is True

            # Wait for idle timeout
            time.sleep(0.1)

            # Should be locked due to idle timeout
            assert short_timeout_cache.is_unlocked is False

    def test_idle_timeout_extends_on_access(self) -> None:
        """Test that idle timeout extends on password access."""
        password = "test_password_123"  # pragma: allowlist secret

        with patch(
            "app.config.settings.master_password_idle_timeout_minutes", 0.01
        ):  # ~0.6 seconds
            result = self.cache.unlock(password)
            assert result is True

            original_idle_expires_at = self.cache.idle_expires_at
            assert original_idle_expires_at is not None

            # Access the password before idle timeout
            time.sleep(0.3)
            retrieved_password = self.cache.get_master_password()
            assert retrieved_password == password
            assert self.cache.is_unlocked is True

            # Idle timeout should have been extended
            assert self.cache.idle_expires_at is not None
            assert self.cache.idle_expires_at > original_idle_expires_at

    def test_idle_timeout_extends_on_verification(self) -> None:
        """Test that idle timeout extends on password verification."""
        password = "test_password_123"  # pragma: allowlist secret

        with patch(
            "app.config.settings.master_password_idle_timeout_minutes", 0.01
        ):  # ~0.6 seconds
            result = self.cache.unlock(password)
            assert result is True

            original_idle_expires_at = self.cache.idle_expires_at
            assert original_idle_expires_at is not None

            # Verify the password before idle timeout
            time.sleep(0.3)
            is_valid = self.cache.verify_password(password)
            assert is_valid is True
            assert self.cache.is_unlocked is True

            # Idle timeout should have been extended
            assert self.cache.idle_expires_at is not None
            assert self.cache.idle_expires_at > original_idle_expires_at

    def test_get_status_includes_idle_info(self) -> None:
        """Test that status includes idle timeout information."""
        password = "test_password_123"  # pragma: allowlist secret

        self.cache.unlock(password)

        status = self.cache.get_status()

        assert "idle_expires_at" in status
        assert "idle_ttl_seconds" in status
        assert status["idle_expires_at"] is not None
        assert status["idle_ttl_seconds"] > 0
        assert status["session_id"] == self.session_id

    def test_extend_ttl_extends_idle_timeout(self) -> None:
        """Test that extending TTL also extends idle timeout."""
        password = "test_password_123"  # pragma: allowlist secret

        self.cache.unlock(password)

        original_idle_expires_at = self.cache.idle_expires_at
        assert original_idle_expires_at is not None

        # Extend TTL
        result = self.cache.extend_ttl(additional_hours=1.0)
        assert result is True

        # Both absolute and idle timeouts should be extended
        assert self.cache.idle_expires_at is not None
        assert self.cache.idle_expires_at > original_idle_expires_at

    def test_refresh_access_extends_idle_timeout(self) -> None:
        """Test that refreshing access extends idle timeout."""
        password = "test_password_123"  # pragma: allowlist secret

        self.cache.unlock(password)

        original_idle_expires_at = self.cache.idle_expires_at
        assert original_idle_expires_at is not None

        # Refresh access
        result = self.cache.refresh_access()
        assert result is True

        # Idle timeout should be extended
        assert self.cache.idle_expires_at is not None
        assert self.cache.idle_expires_at > original_idle_expires_at


class TestMasterPasswordSessionManager:
    """Test cases for MasterPasswordSessionManager."""

    def setup_method(self) -> None:
        """Clean up session manager before each test."""
        # Remove all existing sessions
        all_sessions = list(session_manager._sessions.keys())
        for session_id in all_sessions:
            session_manager.remove_session(session_id)

    def test_get_session_creates_new_session(self) -> None:
        """Test that getting a session creates it if it doesn't exist."""
        session_id = "new-session-456"

        # Initially no sessions
        assert session_manager.get_session_count() == 0

        # Get a session
        cache = session_manager.get_session(session_id)

        assert cache is not None
        assert cache.session_id == session_id
        assert session_manager.get_session_count() == 1

    def test_get_session_returns_existing_session(self) -> None:
        """Test that getting a session returns existing one."""
        session_id = "existing-session-789"

        # Get session twice
        cache1 = session_manager.get_session(session_id)
        cache2 = session_manager.get_session(session_id)

        assert cache1 is cache2  # Should be the same instance
        assert session_manager.get_session_count() == 1

    def test_remove_session(self) -> None:
        """Test removing a session."""
        session_id = "removable-session-123"

        # Create a session
        cache = session_manager.get_session(session_id)
        cache.unlock("test_password")  # pragma: allowlist secret
        assert cache.is_unlocked is True
        assert session_manager.get_session_count() == 1

        # Remove the session
        session_manager.remove_session(session_id)

        assert session_manager.get_session_count() == 0

        # Cache should be locked
        assert cache.is_unlocked is False

    def test_cleanup_expired_sessions(self) -> None:
        """Test cleaning up expired sessions."""
        # Create multiple sessions
        session_ids = ["session-1", "session-2", "session-3"]
        caches = []

        for session_id in session_ids:
            cache = session_manager.get_session(session_id)
            caches.append(cache)

        # Unlock all sessions
        caches[0].unlock("test_password")  # pragma: allowlist secret
        caches[1].unlock("test_password")  # pragma: allowlist secret
        caches[2].unlock("test_password")  # pragma: allowlist secret

        assert session_manager.get_session_count() == 3

        # Manually expire one session by locking it
        caches[0].lock()

        # Clean up expired sessions
        cleaned_count = session_manager.cleanup_expired_sessions()

        assert cleaned_count == 1
        assert session_manager.get_session_count() == 2

        # Remaining sessions should be the unlocked ones
        remaining_sessions = session_manager.get_all_sessions_status()
        remaining_session_ids = {s["session_id"] for s in remaining_sessions}
        assert "session-2" in remaining_session_ids
        assert "session-3" in remaining_session_ids
        assert "session-1" not in remaining_session_ids

    def test_get_all_sessions_status(self) -> None:
        """Test getting status for all sessions."""
        # Create multiple sessions
        session_ids = ["session-a", "session-b"]
        passwords = ["password_a", "password_b"]  # pragma: allowlist secret

        for session_id, password in zip(session_ids, passwords, strict=False):
            cache = session_manager.get_session(session_id)
            cache.unlock(password)

        # Get all sessions status
        all_status = session_manager.get_all_sessions_status()

        assert len(all_status) == 2
        session_ids_in_status = {s["session_id"] for s in all_status}
        assert session_ids_in_status == set(session_ids)

        # Check that status contains expected fields
        for status in all_status:
            assert "session_id" in status
            assert "is_unlocked" in status
            assert "password_id" in status
            assert "idle_expires_at" in status
            assert "idle_ttl_seconds" in status


class TestGetMasterPasswordCache:
    """Test cases for get_master_password_cache function."""

    def test_returns_global_cache_when_session_disabled(self) -> None:
        """Test that global cache is returned when session mode is disabled."""
        with patch("app.config.settings.master_password_per_user_session", False):
            cache = get_master_password_cache("some-session-id")
            # Should return the global singleton cache
            from app.services.master_password import master_password_cache

            assert cache is master_password_cache

    def test_returns_session_cache_when_session_enabled(self) -> None:
        """Test that session cache is returned when session mode is enabled."""
        with patch("app.config.settings.master_password_per_user_session", True):
            session_id = "test-session-123"
            cache = get_master_password_cache(session_id)

            # Should return a session cache
            assert isinstance(cache, SessionMasterPasswordCache)
            assert cache.session_id == session_id

    def test_returns_global_cache_when_no_session_id(self) -> None:
        """Test that global cache is returned when no session ID provided."""
        with patch("app.config.settings.master_password_per_user_session", True):
            cache = get_master_password_cache(None)
            # Should return the global singleton cache when no session ID
            from app.services.master_password import master_password_cache

            assert cache is master_password_cache
