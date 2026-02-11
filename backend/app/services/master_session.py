"""Master session management for admin access using the master password."""

from __future__ import annotations

import hashlib
import secrets
import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def format_master_actor(session_id: str) -> str:
    """Format a stable, non-sensitive actor label for audit events."""
    return f"master-session:{session_id[:16]}"


@dataclass(frozen=True)
class MasterSession:
    """Represents an in-memory master session."""

    session_id: str
    created_at: datetime
    last_activity_at: datetime
    expires_at: datetime
    ip_address: str | None
    user_agent: str | None


class MasterSessionManager:
    """Manages master sessions in memory."""

    def __init__(self) -> None:
        self._sessions: dict[str, MasterSession] = {}
        self._lock = threading.RLock()

    def create_session(
        self,
        ttl_hours: float | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[str, MasterSession]:
        """Create a new master session and return (token, session)."""
        token = secrets.token_urlsafe(64)
        session_id = _hash_token(token)
        now = datetime.now(UTC)
        ttl = timedelta(
            hours=(
                ttl_hours
                if ttl_hours is not None
                else settings.master_password_ttl_hours
            )
        )
        expires_at = now + ttl
        session = MasterSession(
            session_id=session_id,
            created_at=now,
            last_activity_at=now,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        with self._lock:
            self._sessions[session_id] = session
        logger.info(
            "Created master session",
            extra={"session_id": session_id, "expires_at": expires_at.isoformat()},
        )
        return token, session

    def get_session(
        self,
        token: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
        update_activity: bool = True,
    ) -> MasterSession | None:
        """Validate a session token and return the session if valid."""
        if not token:
            return None

        session_id = _hash_token(token)
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return None

            now = datetime.now(UTC)
            if now >= session.expires_at:
                self._sessions.pop(session_id, None)
                return None

            idle_timeout = timedelta(
                minutes=settings.master_password_idle_timeout_minutes
            )
            if now - session.last_activity_at > idle_timeout:
                self._sessions.pop(session_id, None)
                return None

            if session.ip_address and ip_address:
                if not self._is_ip_compatible(session.ip_address, ip_address):
                    return None

            if session.user_agent and user_agent and session.user_agent != user_agent:
                return None

            if update_activity:
                refreshed = MasterSession(
                    session_id=session.session_id,
                    created_at=session.created_at,
                    last_activity_at=now,
                    expires_at=session.expires_at,
                    ip_address=session.ip_address,
                    user_agent=session.user_agent,
                )
                self._sessions[session_id] = refreshed
                session = refreshed

            return session

    def remove_session(self, session_id: str) -> None:
        """Remove a session by ID."""
        with self._lock:
            self._sessions.pop(session_id, None)

    def extend_session(self, session_id: str, additional_hours: float) -> bool:
        """Extend session expiry using the same sliding TTL strategy as unlock."""
        if additional_hours <= 0:
            return False

        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False

            now = datetime.now(UTC)
            updated = MasterSession(
                session_id=session.session_id,
                created_at=session.created_at,
                last_activity_at=now,
                expires_at=now + timedelta(hours=additional_hours),
                ip_address=session.ip_address,
                user_agent=session.user_agent,
            )
            self._sessions[session_id] = updated
            return True

    def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions and return count."""
        with self._lock:
            now = datetime.now(UTC)
            expired = [
                session_id
                for session_id, session in self._sessions.items()
                if now >= session.expires_at
            ]
            for session_id in expired:
                self._sessions.pop(session_id, None)
            return len(expired)

    def _is_ip_compatible(self, original_ip: str, current_ip: str) -> bool:
        """Check if two IPs are compatible, allowing for some network flexibility."""
        import ipaddress

        try:
            orig_addr = ipaddress.ip_address(original_ip)
            curr_addr = ipaddress.ip_address(current_ip)
        except ValueError:
            return False

        if orig_addr == curr_addr:
            return True

        if isinstance(orig_addr, ipaddress.IPv4Address) and isinstance(
            curr_addr, ipaddress.IPv4Address
        ):
            orig_octets = str(orig_addr).split(".")
            curr_octets = str(curr_addr).split(".")
            return (
                len(orig_octets) >= 2
                and len(curr_octets) >= 2
                and orig_octets[0] == curr_octets[0]
                and orig_octets[1] == curr_octets[1]
            )

        if isinstance(orig_addr, ipaddress.IPv6Address) and isinstance(
            curr_addr, ipaddress.IPv6Address
        ):
            orig_parts = str(orig_addr).split(":")
            curr_parts = str(curr_addr).split(":")
            if len(orig_parts) >= 4 and len(curr_parts) >= 4:
                return orig_parts[:4] == curr_parts[:4]

        return False


master_session_manager = MasterSessionManager()
