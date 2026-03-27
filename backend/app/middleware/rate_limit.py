"""Rate limiting middleware for API endpoints."""

from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from redis import asyncio as redis_asyncio  # type: ignore[import-untyped]
from starlette.middleware.base import BaseHTTPMiddleware

if TYPE_CHECKING:
    from app.services.audit import AuditService


@dataclass
class RateLimitResult:
    """Outcome of a rate-limit check."""

    allowed: bool
    remaining: int
    retry_after: float


class RateLimitEntry:
    """Represents a rate limit entry for a key."""

    def __init__(self, window_size: int, max_requests: int) -> None:
        self.window_size = window_size
        self.max_requests = max_requests
        self.requests: list[float] = []
        self.blocked_until = 0.0

    def is_blocked(self, current_time: float) -> bool:
        return current_time < self.blocked_until

    def record(self, current_time: float) -> RateLimitResult:
        cutoff_time = current_time - self.window_size
        self.requests = [
            req_time for req_time in self.requests if req_time > cutoff_time
        ]

        if self.is_blocked(current_time):
            retry_after = max(0.0, self.blocked_until - current_time)
            return RateLimitResult(False, 0, retry_after or self.window_size)

        if len(self.requests) < self.max_requests:
            self.requests.append(current_time)
            remaining = max(0, self.max_requests - len(self.requests))
            return RateLimitResult(True, remaining, self.window_size)

        self.blocked_until = current_time + self.window_size
        return RateLimitResult(False, 0, self.window_size)


class RateLimitStore:
    """Storage abstraction for rate-limit counters."""

    async def hit(
        self, key: str, window: int, max_requests: int
    ) -> RateLimitResult:  # pragma: no cover - interface
        raise NotImplementedError

    async def cleanup(
        self, current_time: float
    ) -> None:  # pragma: no cover - interface
        return None

    async def stats(self) -> dict[str, Any]:  # pragma: no cover - interface
        return {}


class InMemoryRateLimitStore(RateLimitStore):
    def __init__(self) -> None:
        self.entries: dict[str, RateLimitEntry] = {}

    async def hit(self, key: str, window: int, max_requests: int) -> RateLimitResult:
        entry = self.entries.setdefault(key, RateLimitEntry(window, max_requests))
        entry.window_size = window
        entry.max_requests = max_requests
        return entry.record(time.time())

    async def cleanup(self, current_time: float) -> None:
        cutoff_seconds = 3600
        cutoff_time = current_time - cutoff_seconds

        def _collect_expired() -> list[str]:
            expired: list[str] = []
            for key, entry in self.entries.items():
                if entry.is_blocked(current_time):
                    continue
                if not entry.requests or all(
                    req_time < cutoff_time for req_time in entry.requests
                ):
                    expired.append(key)
            return expired

        for key in _collect_expired():
            self.entries.pop(key, None)

    async def stats(self) -> dict[str, Any]:
        current_time = time.time()
        active = sum(
            1
            for entry in self.entries.values()
            if entry.requests or entry.is_blocked(current_time)
        )
        blocked = sum(
            1 for entry in self.entries.values() if entry.is_blocked(current_time)
        )
        return {
            "store": "memory",
            "active_entries": active,
            "blocked_entries": blocked,
            "total_entries": len(self.entries),
        }


RATE_LIMIT_SCRIPT = """
local key = KEYS[1]
local window = tonumber(ARGV[1])
local max_requests = tonumber(ARGV[2])
local current = redis.call('incr', key)
if current == 1 then
  redis.call('expire', key, window)
end
local ttl = redis.call('ttl', key)
return {current, ttl}
"""


class RedisRateLimitStore(RateLimitStore):
    def __init__(self, redis_url: str, prefix: str = "ratelimit") -> None:
        if redis_asyncio is None:
            raise RuntimeError("redis asyncio client is not installed")

        self.prefix = prefix.rstrip(":")
        self.redis = redis_asyncio.from_url(redis_url, decode_responses=True)

    async def hit(self, key: str, window: int, max_requests: int) -> RateLimitResult:
        namespaced = f"{self.prefix}:{key}"
        # In redis-py 5.x, eval() uses *keys_and_args as positional arguments
        current, ttl = await self.redis.eval(
            RATE_LIMIT_SCRIPT, 1, namespaced, window, max_requests
        )  # type: ignore[arg-type]
        current_int = int(current)
        ttl_int = int(ttl) if ttl is not None else window
        allowed = current_int <= max_requests
        remaining = max(0, max_requests - current_int)
        retry_after = max(0, ttl_int)
        return RateLimitResult(allowed, remaining, retry_after or window)

    async def stats(self) -> dict[str, Any]:
        return {"store": "redis", "prefix": self.prefix}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce rate limiting on API endpoints."""

    def __init__(
        self,
        app: Any,
        api_key_window: int = 60,
        api_key_max_requests: int = 60,
        ip_window: int = 60,
        ip_max_requests: int = 10,
        trusted_proxies: list[str] | None = None,
        backend: str = "memory",
        redis_url: str | None = None,
        redis_prefix: str = "ratelimit",
    ) -> None:
        super().__init__(app)
        self.api_key_window = api_key_window
        self.api_key_max_requests = api_key_max_requests
        self.ip_window = ip_window
        self.ip_max_requests = ip_max_requests
        self.logger = logging.getLogger(__name__)

        # Parse trusted proxy CIDR ranges
        self.trusted_proxies: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
        if trusted_proxies:
            for proxy in trusted_proxies:
                try:
                    self.trusted_proxies.append(
                        ipaddress.ip_network(proxy, strict=False)
                    )
                except ValueError:
                    continue

        self._cleanup_task: asyncio.Task | None = None
        self._cleanup_started = False

        self.store: RateLimitStore
        backend_choice = backend.lower().strip()
        if backend_choice == "redis" and redis_url:
            try:
                self.store = RedisRateLimitStore(redis_url, redis_prefix)
            except Exception as exc:  # pragma: no cover - configuration dependent
                self.logger.warning("Falling back to in-memory rate limiting: %s", exc)
                self.store = InMemoryRateLimitStore()
        else:
            self.store = InMemoryRateLimitStore()

    @property
    def ip_limits(self) -> dict[str, RateLimitEntry]:
        if isinstance(self.store, InMemoryRateLimitStore):
            return {
                key[len("ip:") :]: entry
                for key, entry in self.store.entries.items()
                if key.startswith("ip:")
            }
        return getattr(self, "_ip_limits", {})

    @ip_limits.setter
    def ip_limits(self, value: dict[str, RateLimitEntry]) -> None:
        if isinstance(self.store, InMemoryRateLimitStore):
            for key in list(self.store.entries.keys()):
                if key.startswith("ip:"):
                    self.store.entries.pop(key, None)
            for ip_key, entry in value.items():
                self.store.entries[f"ip:{ip_key}"] = entry
        else:
            self._ip_limits = value

    @property
    def api_key_limits(self) -> dict[str, RateLimitEntry]:
        if isinstance(self.store, InMemoryRateLimitStore):
            return {
                key[len("api:") :]: entry
                for key, entry in self.store.entries.items()
                if key.startswith("api:")
            }
        return getattr(self, "_api_key_limits", {})

    @api_key_limits.setter
    def api_key_limits(self, value: dict[str, RateLimitEntry]) -> None:
        if isinstance(self.store, InMemoryRateLimitStore):
            for key in list(self.store.entries.keys()):
                if key.startswith("api:"):
                    self.store.entries.pop(key, None)
            for api_key, entry in value.items():
                self.store.entries[f"api:{api_key}"] = entry
        else:
            self._api_key_limits = value

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        if not self._cleanup_started and isinstance(self.store, InMemoryRateLimitStore):
            self._cleanup_started = True
            try:
                loop = asyncio.get_running_loop()
                self._cleanup_task = loop.create_task(self._cleanup_old_entries())
            except RuntimeError:
                pass

        if await self._has_valid_master_session(request):
            return await call_next(request)

        if self._should_skip_rate_limit(request.url.path):
            return await call_next(request)

        time.time()
        source_ip = self._get_client_ip(request)
        api_key = self._extract_api_key(request)
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest() if api_key else None

        ip_result: RateLimitResult | None = None
        api_key_result: RateLimitResult | None = None

        if source_ip:
            try:
                ip_result = await self.store.hit(
                    f"ip:{source_ip}", self.ip_window, self.ip_max_requests
                )
            except Exception as exc:  # pragma: no cover - fallback path
                self.logger.warning("Falling back to in-memory rate limiting: %s", exc)
                self.store = InMemoryRateLimitStore()
                ip_result = await self.store.hit(
                    f"ip:{source_ip}", self.ip_window, self.ip_max_requests
                )
            if not ip_result.allowed:
                await self._log_rate_limit_violation(
                    request,
                    source_ip,
                    None,
                    "IP_RATE_LIMIT",
                    f"IP address blocked for {self.ip_window} seconds",
                )
                return self._create_rate_limit_response(
                    ip_result.retry_after,
                    self.ip_max_requests,
                    self.ip_window,
                    "Rate limit exceeded. Please try again later.",
                )

        if api_key_hash:
            try:
                api_key_result = await self.store.hit(
                    f"api:{api_key_hash}",
                    self.api_key_window,
                    self.api_key_max_requests,
                )
            except Exception as exc:  # pragma: no cover - fallback path
                self.logger.warning("Falling back to in-memory rate limiting: %s", exc)
                self.store = InMemoryRateLimitStore()
                api_key_result = await self.store.hit(
                    f"api:{api_key_hash}",
                    self.api_key_window,
                    self.api_key_max_requests,
                )

            if not api_key_result.allowed:
                await self._log_rate_limit_violation(
                    request,
                    source_ip,
                    api_key_hash,
                    "API_KEY_RATE_LIMIT",
                    f"API key rate limit exceeded: {self.api_key_max_requests}/{self.api_key_window}",
                )
                return self._create_rate_limit_response(
                    api_key_result.retry_after,
                    self.api_key_max_requests,
                    self.api_key_window,
                    "Rate limit exceeded for this API key.",
                    api_key_result.remaining,
                )

        response = await call_next(request)

        if ip_result:
            response.headers["X-RateLimit-Limit-IP"] = str(self.ip_max_requests)
            response.headers["X-RateLimit-Remaining-IP"] = str(
                max(0, ip_result.remaining)
            )
            response.headers["X-RateLimit-Window-IP"] = str(self.ip_window)

        if api_key_result:
            response.headers["X-RateLimit-Limit-Key"] = str(self.api_key_max_requests)
            response.headers["X-RateLimit-Remaining-Key"] = str(
                max(0, api_key_result.remaining)
            )
            response.headers["X-RateLimit-Window-Key"] = str(self.api_key_window)

        return response

    def _should_skip_rate_limit(self, path: str) -> bool:
        skip_prefixes = (
            "/health",
            "/ready",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
        )
        return any(path.startswith(prefix) for prefix in skip_prefixes)

    def _create_rate_limit_response(
        self,
        retry_after: float,
        limit: int,
        window: int,
        detail: str,
        remaining: int = 0,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": detail},
            headers={
                "Retry-After": str(int(retry_after)),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Window": str(window),
                "X-RateLimit-Remaining": str(remaining),
            },
        )

    def get_rate_limit_stats(self) -> dict[str, Any]:
        """Return rate limit statistics for in-memory tracking."""

        def _summarize(prefix: str) -> tuple[int, int, int]:
            if not isinstance(self.store, InMemoryRateLimitStore):
                return (0, 0, 0)
            current_time = time.time()
            entries = [
                entry
                for key, entry in self.store.entries.items()
                if key.startswith(prefix)
            ]
            active = sum(
                1
                for entry in entries
                if entry.requests or entry.is_blocked(current_time)
            )
            blocked = sum(1 for entry in entries if entry.is_blocked(current_time))
            return active, blocked, len(entries)

        active_ip, blocked_ip, total_ip = _summarize("ip:")
        active_key, blocked_key, total_key = _summarize("api:")

        return {
            "active_ip_limits": active_ip,
            "active_key_limits": active_key,
            "blocked_ips": blocked_ip,
            "blocked_keys": blocked_key,
            "total_ip_entries": total_ip,
            "total_key_entries": total_key,
            "ip_limit_config": {
                "window_seconds": self.ip_window,
                "max_requests": self.ip_max_requests,
            },
            "api_key_limit_config": {
                "window_seconds": self.api_key_window,
                "max_requests": self.api_key_max_requests,
            },
        }

    def _purge_stale_entries(self, current_time: float) -> None:
        """Remove stale entries from the in-memory store."""
        if not isinstance(self.store, InMemoryRateLimitStore):
            return

        cutoff_seconds = 3600
        cutoff_time = current_time - cutoff_seconds

        def _should_remove(entry: RateLimitEntry) -> bool:
            if entry.is_blocked(current_time):
                return False
            if not entry.requests:
                return True
            return all(req_time < cutoff_time for req_time in entry.requests)

        for key in list(self.store.entries.keys()):
            if _should_remove(self.store.entries[key]):
                self.store.entries.pop(key, None)

    def _get_client_ip(self, request: Request) -> str | None:
        """Get the real client IP, validating forwarded headers only from trusted proxies."""
        direct_ip = None
        if hasattr(request, "client") and request.client:
            direct_ip = request.client.host

        is_trusted_proxy = False
        if direct_ip and self.trusted_proxies:
            try:
                client_ip = ipaddress.ip_address(direct_ip)
                is_trusted_proxy = any(
                    client_ip in proxy_network for proxy_network in self.trusted_proxies
                )
            except ValueError:
                is_trusted_proxy = False

        if is_trusted_proxy:
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                original_ip = forwarded_for.split(",")[0].strip()
                if original_ip:
                    return original_ip

            real_ip = request.headers.get("X-Real-IP")
            if real_ip:
                cleaned_ip = real_ip.strip()
                if cleaned_ip:
                    return cleaned_ip

        return direct_ip

    def _extract_api_key(self, request: Request) -> str | None:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[len("Bearer ") :]
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return api_key
        return None

    def _get_audit_service(self, request: Request) -> AuditService | None:
        try:
            if not hasattr(request, "state"):
                return None

            state = request.state
            if not hasattr(state, "db"):
                return None

            db = state.db
            if db is not None:
                from app.services.audit import AuditService

                return AuditService(db)
        except Exception:
            pass
        return None

    async def _log_rate_limit_violation(
        self,
        request: Request,
        source_ip: str | None,
        api_key_hash: str | None,
        violation_type: str,
        message: str,
    ) -> None:
        audit_service = self._get_audit_service(request)
        if not audit_service:
            return

        path_parts = request.url.path.strip("/").split("/")
        network_id = None

        if (
            len(path_parts) >= 3
            and path_parts[0] == "api"
            and path_parts[1] == "devices"
            and len(path_parts) > 2
        ):
            device_id = path_parts[2]
            if device_id:
                network_id = "unknown"

        details = {
            "source_ip": source_ip,
            "violation_type": violation_type,
            "message": message,
            "path": request.url.path,
            "method": request.method,
            "user_agent": request.headers.get("User-Agent", "Unknown"),
        }

        if api_key_hash:
            details["api_key_hash"] = api_key_hash

        await audit_service.log_event(
            network_id=network_id or "unknown",
            actor=source_ip or "unknown",
            action="RATE_LIMIT_VIOLATION",
            resource_type="rate_limit",
            resource_id=api_key_hash or source_ip or "unknown",
            details=details,
        )

    async def _cleanup_old_entries(self) -> None:
        while True:
            try:
                await asyncio.sleep(300)
                current_time = time.time()
                self._purge_stale_entries(current_time)
                await self.store.cleanup(current_time)

            except asyncio.CancelledError:
                break
            except Exception:
                pass

    async def stats(self) -> dict[str, Any]:
        base_stats = await self.store.stats()
        base_stats.update(
            {
                "ip_limit_config": {
                    "window_seconds": self.ip_window,
                    "max_requests": self.ip_max_requests,
                },
                "api_key_limit_config": {
                    "window_seconds": self.api_key_window,
                    "max_requests": self.api_key_max_requests,
                },
            }
        )
        return base_stats

    async def _has_valid_master_session(self, request: Request) -> bool:
        state = getattr(request, "state", None)
        if state is not None:
            session = None
            if hasattr(state, "__dict__"):
                if "master_session" in state.__dict__:
                    session = state.__dict__.get("master_session")
            elif hasattr(state, "master_session"):
                session = getattr(state, "master_session", None)
            if session is not None:
                return True

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Master "):
            return False

        session_token = auth_header[len("Master ") :]
        if not session_token:
            return False

        try:
            from app.services.master_session import master_session_manager

            client_ip = self._get_client_ip(request)
            user_agent = request.headers.get("User-Agent")
            return (
                master_session_manager.get_session(
                    session_token,
                    ip_address=client_ip,
                    user_agent=user_agent,
                )
                is not None
            )
        except Exception:
            return False
