"""Master password management service for in-memory caching.

This service caches the master password securely in memory only (no disk persistence)
with automatic expiration, idle timeout, and session management capabilities.
"""

from __future__ import annotations

import hashlib
import secrets
import threading
from datetime import UTC, datetime, timedelta
from typing import ClassVar

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

PASSWORD_ID_LENGTH = 16


class BaseMasterPasswordCache:
    """Base class for secure in-memory master password cache.

    Provides common functionality for both global and session-based caches
    with automatic expiration, idle timeout, and secure clearing capabilities.
    """

    PASSWORD_ID_LENGTH: ClassVar[int] = PASSWORD_ID_LENGTH

    def __init__(self, cache_identifier: str = "global") -> None:
        """Initialize the master password cache.

        Args:
            cache_identifier: Identifier for logging and tracking
        """
        self.cache_identifier = cache_identifier
        self._cache_lock = threading.RLock()
        self._master_password: str | None = None
        self._password_id: str | None = None
        self._expires_at: datetime | None = None
        self._idle_expires_at: datetime | None = None
        self._access_count = 0
        self._last_access: datetime | None = None
        self._is_locked = True

        self._ttl = timedelta(hours=settings.master_password_ttl_hours)
        self._idle_timeout = timedelta(
            minutes=settings.master_password_idle_timeout_minutes
        )

        logger.info(
            "Master password cache initialized",
            extra={
                "cache_type": self.cache_identifier,
                "ttl_hours": self._ttl.total_seconds() / 3600,
                "idle_timeout_minutes": self._idle_timeout.total_seconds() / 60,
            },
        )

    def _is_expired(self) -> bool:
        """Check if the cache has expired."""
        now = datetime.now(UTC)

        # Check absolute expiration
        if self._expires_at is None or now >= self._expires_at:
            return True

        # Check idle timeout expiration
        return self._idle_expires_at is not None and now >= self._idle_expires_at

    @property
    def is_unlocked(self) -> bool:
        """Check if the cache is currently unlocked with a valid password."""
        if self._is_locked:
            return False

        if self._is_expired():
            self._lock_cache()
            return False

        return True

    @property
    def password_id(self) -> str | None:
        """Get the ID of the currently cached password."""
        return self._password_id

    @property
    def expires_at(self) -> datetime | None:
        """Get the absolute expiration time of the cached password."""
        return self._expires_at

    @property
    def idle_expires_at(self) -> datetime | None:
        """Get the idle expiration time of the cached password."""
        return self._idle_expires_at

    @property
    def access_count(self) -> int:
        """Get the number of times the cached password has been accessed."""
        return self._access_count

    @property
    def last_access(self) -> datetime | None:
        """Get the last access time of the cached password."""
        return self._last_access

    def _generate_password_id(self, master_password: str) -> str:
        """Generate a unique ID for the password."""
        return hashlib.sha256(
            f"{master_password}{secrets.token_hex(8)}".encode()
        ).hexdigest()[: self.PASSWORD_ID_LENGTH]

    def _set_expiration_times(self, ttl_hours: float | None) -> None:
        """Set absolute and idle expiration times."""
        now = datetime.now(UTC)
        ttl = timedelta(hours=ttl_hours) if ttl_hours is not None else self._ttl

        self._expires_at = now + ttl
        self._idle_expires_at = now + self._idle_timeout

    def _update_access_tracking(self, increment_count: bool = True) -> None:
        """Update access tracking and extend idle timeout."""
        now = datetime.now(UTC)

        if increment_count:
            self._access_count += 1

        self._last_access = now
        self._idle_expires_at = now + self._idle_timeout

    def unlock(self, master_password: str, ttl_hours: float | None = None) -> bool:
        """Unlock the cache with a master password.

        Args:
            master_password: The master password to cache
            ttl_hours: Optional custom TTL in hours (overrides default)

        Returns:
            True if unlock was successful, False if master_password is invalid

        Raises:
            ValueError: If master_password is empty
        """
        if not master_password:
            raise ValueError("Master password cannot be empty")

        with self._cache_lock:
            try:
                self._lock_cache()

                self._master_password = master_password
                self._password_id = self._generate_password_id(master_password)
                self._set_expiration_times(ttl_hours)

                self._access_count = 0
                self._last_access = None
                self._is_locked = False

                logger.info(
                    "Master password cache unlocked",
                    extra={
                        "cache_type": self.cache_identifier,
                        "expires_at": (
                            self._expires_at.isoformat() if self._expires_at else None
                        ),
                        "idle_expires_at": (
                            self._idle_expires_at.isoformat()
                            if self._idle_expires_at
                            else None
                        ),
                        "ttl_hours": self._calculate_ttl_hours(),
                    },
                )
                return True

            except Exception as e:
                logger.error(
                    "Failed to unlock master password cache",
                    extra={
                        "cache_type": self.cache_identifier,
                        "error": str(e),
                    },
                    exc_info=True,
                )
                self._lock_cache()
                return False

    def lock(self) -> None:
        """Manually lock the cache and clear all cached data."""
        with self._cache_lock:
            self._lock_cache()
            logger.info(
                "Master password cache manually locked",
                extra={"cache_type": self.cache_identifier},
            )

    def clear(self) -> None:
        """Clear the cache (alias for lock) for test compatibility."""
        self.lock()

    def _lock_cache(self) -> None:
        """Internal method to lock the cache and clear sensitive data."""
        self._is_locked = True
        self._master_password = None
        self._password_id = None
        self._expires_at = None
        self._idle_expires_at = None
        self._access_count = 0
        self._last_access = None

    def get_master_password(self) -> str:
        """Get the cached master password.

        Returns:
            The master password string

        Raises:
            ValueError: If cache is locked or password has expired
        """
        if not self.is_unlocked:
            raise ValueError("Master password cache is locked or expired")

        with self._cache_lock:
            if self._master_password is None:
                raise ValueError("No master password available")

            self._update_access_tracking()
            return self._master_password

    def verify_password(self, test_password: str) -> bool:
        """Verify if a test password matches the cached password.

        Args:
            test_password: Password to verify against the cached password

        Returns:
            True if passwords match, False otherwise or if cache is locked
        """
        if not self.is_unlocked or self._master_password is None:
            return False

        self._update_access_tracking(increment_count=False)

        return secrets.compare_digest(
            test_password.encode(), self._master_password.encode()
        )

    def extend_ttl(self, additional_hours: float = 1.0) -> bool:
        """Extend the TTL of the current cached password.

        Args:
            additional_hours: Additional hours to extend the TTL by

        Returns:
            True if TTL was extended, False if cache is locked

        Raises:
            ValueError: If additional_hours is not positive
        """
        if additional_hours <= 0:
            raise ValueError("Additional hours must be positive")

        if not self.is_unlocked:
            return False

        with self._cache_lock:
            if self._expires_at is not None:
                old_expires_at = self._expires_at
                now = datetime.now(UTC)
                self._expires_at = now + timedelta(hours=additional_hours)
                self._idle_expires_at = now + self._idle_timeout

                logger.info(
                    "Master password cache TTL extended",
                    extra={
                        "cache_type": self.cache_identifier,
                        "old_expires_at": old_expires_at.isoformat(),
                        "new_expires_at": self._expires_at.isoformat(),
                        "additional_hours": additional_hours,
                    },
                )
                return True

            return False

    def refresh_access(self) -> bool:
        """Refresh the last access time and idle timeout without incrementing counter.

        Returns:
            True if access was refreshed, False if cache is locked
        """
        if not self.is_unlocked:
            return False

        with self._cache_lock:
            self._update_access_tracking(increment_count=False)
            return True

    def get_status(self) -> dict:
        """Get the current status of the cache (safe for logging/monitoring).

        Returns:
            Dictionary with cache status information (no sensitive data)
        """
        with self._cache_lock:
            now = datetime.now(UTC)
            base_status = {
                "is_unlocked": self.is_unlocked,
                "password_id": self._password_id if not self._is_locked else None,
                "expires_at": (
                    self._expires_at.isoformat() if self._expires_at else None
                ),
                "idle_expires_at": (
                    self._idle_expires_at.isoformat() if self._idle_expires_at else None
                ),
                "access_count": self._access_count,
                "last_access": (
                    self._last_access.isoformat() if self._last_access else None
                ),
                "ttl_seconds": (
                    (self._expires_at - now).total_seconds()
                    if self._expires_at and now < self._expires_at
                    else 0
                ),
                "idle_ttl_seconds": (
                    (self._idle_expires_at - now).total_seconds()
                    if self._idle_expires_at and now < self._idle_expires_at
                    else 0
                ),
            }

            return self._add_status_fields(base_status)

    def _calculate_ttl_hours(self) -> float:
        """Calculate remaining TTL in hours."""
        if not self._expires_at:
            return 0.0
        remaining_seconds = (self._expires_at - datetime.now(UTC)).total_seconds()
        return max(0.0, remaining_seconds / 3600)

    def _add_status_fields(self, base_status: dict) -> dict:
        """Add subclass-specific status fields."""
        return base_status


class SessionMasterPasswordCache(BaseMasterPasswordCache):
    """Session-based secure in-memory cache for master password.

    Extends BaseMasterPasswordCache with session-specific functionality.
    """

    def __init__(self, session_id: str) -> None:
        """Initialize a session-based master password cache.

        Args:
            session_id: Unique identifier for the user session
        """
        super().__init__(f"session:{session_id}")
        self.session_id = session_id

    def _add_status_fields(self, base_status: dict) -> dict:
        """Add session ID to status."""
        base_status["session_id"] = self.session_id
        return base_status


class MasterPasswordCache(BaseMasterPasswordCache):
    """Global secure in-memory cache for master password.

    Provides a singleton instance for application-wide master password caching.
    """

    _instance: ClassVar[MasterPasswordCache | None] = None
    _initialized: ClassVar[bool] = False

    def __new__(cls) -> MasterPasswordCache:
        """Create or return the singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the global master password cache (singleton pattern)."""
        # Check if instance is already initialized by checking the class attribute
        if (
            hasattr(MasterPasswordCache, "_initialized")
            and MasterPasswordCache._initialized
        ):
            return

        super().__init__("global")
        MasterPasswordCache._initialized = True

    @classmethod
    def get_instance(cls) -> MasterPasswordCache:
        """Get the singleton instance of the master password cache."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


class MasterPasswordSessionManager:
    """Manages multiple session-based master password caches."""

    def __init__(self) -> None:
        """Initialize the session manager."""
        self._sessions: dict[str, SessionMasterPasswordCache] = {}
        self._manager_lock = threading.RLock()

    def get_session(self, session_id: str) -> SessionMasterPasswordCache:
        """Get or create a session cache for the given session ID.

        Args:
            session_id: Unique identifier for the user session

        Returns:
            SessionMasterPasswordCache instance for the session
        """
        with self._manager_lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = SessionMasterPasswordCache(session_id)
                logger.info(
                    "Created new session cache",
                    extra={"session_id": session_id},
                )
            return self._sessions[session_id]

    def remove_session(self, session_id: str) -> None:
        """Remove a session cache and lock it.

        Args:
            session_id: Session ID to remove
        """
        with self._manager_lock:
            if session_id in self._sessions:
                session_cache = self._sessions[session_id]
                session_cache.lock()
                del self._sessions[session_id]
                logger.info(
                    "Removed session cache",
                    extra={"session_id": session_id},
                )

    def cleanup_expired_sessions(self) -> int:
        """Clean up expired session caches.

        Returns:
            Number of sessions cleaned up
        """
        with self._manager_lock:
            expired_session_ids = [
                session_id
                for session_id, cache in self._sessions.items()
                if cache._is_expired()
            ]

            for session_id in expired_session_ids:
                self.remove_session(session_id)

            if expired_session_ids:
                logger.info(
                    "Cleaned up expired sessions",
                    extra={
                        "expired_sessions": expired_session_ids,
                        "count": len(expired_session_ids),
                    },
                )

            return len(expired_session_ids)

    def get_all_sessions_status(self) -> list[dict]:
        """Get status of all sessions.

        Returns:
            List of session status dictionaries
        """
        with self._manager_lock:
            return [cache.get_status() for cache in self._sessions.values()]

    def get_session_count(self) -> int:
        """Get the number of active sessions.

        Returns:
            Number of active sessions
        """
        with self._manager_lock:
            return len(self._sessions)


# Global instances
master_password_cache = MasterPasswordCache.get_instance()
session_manager = MasterPasswordSessionManager()


def get_master_password_cache(session_id: str | None = None) -> BaseMasterPasswordCache:
    """Get the appropriate master password cache instance.

    Args:
        session_id: Optional session ID for session-based caching

    Returns:
        BaseMasterPasswordCache instance (global or session-based)
    """
    if settings.master_password_per_user_session and session_id:
        return session_manager.get_session(session_id)
    return master_password_cache
