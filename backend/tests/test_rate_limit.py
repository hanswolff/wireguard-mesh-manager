"""Tests for rate limiting middleware."""

from __future__ import annotations

import ipaddress
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import Request, Response

from app.middleware.rate_limit import RateLimitEntry, RateLimitMiddleware


class TestRateLimitEntry:
    """Tests for RateLimitEntry class."""

    def test_rate_limit_entry_initialization(self) -> None:
        entry = RateLimitEntry(window_size=60, max_requests=10)
        assert entry.window_size == 60
        assert entry.max_requests == 10
        assert entry.requests == []
        assert entry.blocked_until == 0.0

    def test_is_allowed_under_limit(self) -> None:
        entry = RateLimitEntry(window_size=60, max_requests=5)
        current_time = time.time()

        for i in range(5):
            result = entry.record(current_time + i)
            assert result.allowed is True

        result = entry.record(current_time + 5)
        assert result.allowed is False

    def test_is_blocked(self) -> None:
        entry = RateLimitEntry(window_size=60, max_requests=1)
        current_time = time.time()

        result = entry.record(current_time)
        assert result.allowed is True
        assert entry.is_blocked(current_time) is False

        result = entry.record(current_time + 1)
        assert result.allowed is False
        assert entry.is_blocked(current_time + 1) is True

    def test_window_cleanup(self) -> None:
        entry = RateLimitEntry(window_size=10, max_requests=2)
        current_time = time.time()

        result = entry.record(current_time)
        assert result.allowed is True
        result = entry.record(current_time + 1)
        assert result.allowed is True

        future_time = current_time + 15

        result = entry.record(future_time)
        assert result.allowed is True
        result = entry.record(future_time + 1)
        assert result.allowed is True

    def test_empty_requests_cleanup_logic(self) -> None:
        entry = RateLimitEntry(window_size=60, max_requests=10)
        current_time = time.time()

        # Test cleanup logic with empty requests list
        assert entry.is_blocked(current_time) is False
        assert len(entry.requests) == 0


class TestRateLimitMiddleware:
    """Tests for RateLimitMiddleware class."""

    @pytest.fixture
    def mock_app(self) -> Mock:
        """Create a mock FastAPI app."""
        return Mock()

    @pytest.fixture
    def middleware(self, mock_app: Mock) -> RateLimitMiddleware:
        """Create a RateLimitMiddleware instance with test configuration."""
        return RateLimitMiddleware(
            mock_app,
            api_key_window=60,
            api_key_max_requests=10,
            ip_window=60,
            ip_max_requests=5,
        )

    @pytest.fixture
    def mock_request(self) -> Mock:
        request = Mock(spec=["url", "method", "client", "headers", "state"])
        request.url = Mock()
        request.url.path = "/test"
        request.method = "GET"
        request.client = Mock()
        request.client.host = "192.168.1.100"
        request.headers = {}
        request.state = Mock()
        request.state.db = None
        return request

    @pytest.fixture
    def mock_call_next(self) -> Mock:
        response = Mock(spec=Response)
        response.headers = {}
        mock_call_next = AsyncMock(return_value=response)
        return mock_call_next

    async def test_should_skip_rate_limit(
        self, middleware: RateLimitMiddleware
    ) -> None:
        """Test that certain paths are skipped from rate limiting."""
        # Health endpoints
        assert middleware._should_skip_rate_limit("/health") is True
        assert middleware._should_skip_rate_limit("/ready") is True

        # Documentation endpoints
        assert middleware._should_skip_rate_limit("/docs") is True
        assert middleware._should_skip_rate_limit("/redoc") is True
        assert middleware._should_skip_rate_limit("/openapi.json") is True

        # API endpoints should not be skipped
        assert middleware._should_skip_rate_limit("/api/devices/test") is False
        assert middleware._should_skip_rate_limit("/devices/test") is False

    def test_get_client_ip(self, middleware: RateLimitMiddleware) -> None:
        """Test client IP extraction."""
        middleware.trusted_proxies = [ipaddress.ip_network("0.0.0.0/0")]

        # Test with X-Forwarded-For header
        request = Mock(spec=Request)
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.headers = {"X-Forwarded-For": "203.0.113.1, 192.168.1.1"}
        assert middleware._get_client_ip(request) == "203.0.113.1"

        # Test with X-Real-IP header
        request.headers = {"X-Real-IP": "203.0.113.2"}
        assert middleware._get_client_ip(request) == "203.0.113.2"

        # Test with client host
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.100"
        assert middleware._get_client_ip(request) == "192.168.1.100"

        # Test with no client
        request.client = None
        assert middleware._get_client_ip(request) is None

    def test_extract_api_key(self, middleware: RateLimitMiddleware) -> None:
        """Test API key extraction."""
        # Test with valid Bearer token
        request = Mock(spec=Request)
        request.headers = {"Authorization": "Bearer test-api-key-123"}
        assert middleware._extract_api_key(request) == "test-api-key-123"

        # Test with missing Authorization header
        request.headers = {}
        assert middleware._extract_api_key(request) is None

        # Test with invalid Authorization header
        request.headers = {"Authorization": "Basic dGVzdDp0ZXN0"}
        assert middleware._extract_api_key(request) is None

    async def test_ip_rate_limiting(
        self,
        middleware: RateLimitMiddleware,
        mock_request: Mock,
        mock_call_next: AsyncMock,
    ) -> None:
        """Test IP-based rate limiting."""
        mock_request.client.host = "192.168.1.100"

        # Make requests up to the limit
        for _i in range(5):
            response = await middleware.dispatch(mock_request, mock_call_next)
            assert response is not None

        # Next request should return a 429 response
        response = await middleware.dispatch(mock_request, mock_call_next)
        assert response.status_code == 429
        assert "Rate limit exceeded" in response.body.decode()

    async def test_api_key_rate_limiting(
        self, middleware: RateLimitMiddleware, mock_call_next: AsyncMock
    ) -> None:
        """Test API key-based rate limiting."""
        # Create a separate mock for this test without client IP
        request = Mock(spec=["url", "method", "headers"])
        request.url = Mock()
        request.url.path = "/test"
        request.method = "GET"
        request.headers = {"Authorization": "Bearer test-api-key-123"}

        # Make requests up to the limit
        for _i in range(10):
            response = await middleware.dispatch(request, mock_call_next)
            assert response is not None

        # Next request should return a 429 response
        response = await middleware.dispatch(request, mock_call_next)
        assert response.status_code == 429
        assert "Rate limit exceeded" in response.body.decode()

    async def test_rate_limit_headers(
        self,
        middleware: RateLimitMiddleware,
        mock_request: Mock,
        mock_call_next: AsyncMock,
    ) -> None:
        """Test that rate limit headers are added to responses."""
        mock_request.client.host = "192.168.1.100"
        mock_request.headers = {"Authorization": "Bearer test-api-key-123"}

        response = await middleware.dispatch(mock_request, mock_call_next)

        # Check IP rate limit headers
        assert response.headers["X-RateLimit-Limit-IP"] == "5"
        assert response.headers["X-RateLimit-Window-IP"] == "60"
        assert response.headers["X-RateLimit-Remaining-IP"] == "4"  # Used 1 out of 5

        # Check API key rate limit headers
        assert response.headers["X-RateLimit-Limit-Key"] == "10"
        assert response.headers["X-RateLimit-Window-Key"] == "60"
        assert response.headers["X-RateLimit-Remaining-Key"] == "9"  # Used 1 out of 10

    async def test_get_rate_limit_stats(self, middleware: RateLimitMiddleware) -> None:
        """Test rate limit statistics collection."""
        stats = middleware.get_rate_limit_stats()

        expected_keys = [
            "active_ip_limits",
            "active_key_limits",
            "blocked_ips",
            "blocked_keys",
            "total_ip_entries",
            "total_key_entries",
            "ip_limit_config",
            "api_key_limit_config",
        ]

        for key in expected_keys:
            assert key in stats

        assert stats["ip_limit_config"]["window_seconds"] == 60
        assert stats["ip_limit_config"]["max_requests"] == 5
        assert stats["api_key_limit_config"]["window_seconds"] == 60
        assert stats["api_key_limit_config"]["max_requests"] == 10

    async def test_audit_logging_setup(self, middleware: RateLimitMiddleware) -> None:
        mock_request = Mock(spec=["url", "method"])
        audit_service = middleware._get_audit_service(mock_request)
        assert audit_service is None

    async def test_no_client_ip(
        self, middleware: RateLimitMiddleware, mock_call_next: AsyncMock
    ) -> None:
        """Test behavior when no client IP is available."""
        request = Mock(spec=["url", "method", "headers", "state"])
        request.url = Mock()
        request.url.path = "/test"
        request.method = "GET"
        request.headers = {}
        request.state = Mock()
        request.state.db = None
        request.client = None

        response = await middleware.dispatch(request, mock_call_next)
        assert response is not None

    async def test_malformed_forwarded_header(
        self, middleware: RateLimitMiddleware
    ) -> None:
        """Test handling of malformed X-Forwarded-For header."""
        request = Mock(spec=Request)
        middleware.trusted_proxies = [ipaddress.ip_network("0.0.0.0/0")]
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.headers = {"X-Forwarded-For": "  "}
        assert middleware._get_client_ip(request) == "127.0.0.1"

        request.headers = {"X-Forwarded-For": ""}
        assert (
            middleware._get_client_ip(request) == "127.0.0.1"
        )  # empty string is falsy

        request.headers = {"X-Forwarded-For": "  192.168.1.1  "}
        assert middleware._get_client_ip(request) == "192.168.1.1"

    async def test_cleanup_task_starts_on_first_request(
        self,
        middleware: RateLimitMiddleware,
        mock_request: Mock,
        mock_call_next: AsyncMock,
    ) -> None:
        """Test that cleanup task starts on first request."""
        assert middleware._cleanup_started is False
        assert middleware._cleanup_task is None

        await middleware.dispatch(mock_request, mock_call_next)

        assert middleware._cleanup_started is True
        assert middleware._cleanup_task is not None

    async def test_rate_limit_response_creation(
        self, middleware: RateLimitMiddleware
    ) -> None:
        """Test the _create_rate_limit_response helper method."""
        response = middleware._create_rate_limit_response(
            retry_after=60.0,
            limit=100,
            window=3600,
            detail="Too many requests",
            remaining=0,
        )

        assert response.status_code == 429
        assert "Too many requests" in response.body.decode()
        assert response.headers["Retry-After"] == "60"
        assert response.headers["X-RateLimit-Limit"] == "100"
        assert response.headers["X-RateLimit-Window"] == "3600"
        assert response.headers["X-RateLimit-Remaining"] == "0"

    @patch("asyncio.get_running_loop")
    async def test_cleanup_task_runtime_error(
        self,
        mock_get_loop: Mock,
        middleware: RateLimitMiddleware,
        mock_request: Mock,
        mock_call_next: AsyncMock,
    ) -> None:
        """Test handling of RuntimeError when no event loop is running."""
        mock_get_loop.side_effect = RuntimeError("No running loop")

        await middleware.dispatch(mock_request, mock_call_next)

        assert middleware._cleanup_started is True
        assert middleware._cleanup_task is None

    async def test_concurrent_requests_same_ip(
        self, middleware: RateLimitMiddleware, mock_call_next: AsyncMock
    ) -> None:
        """Test concurrent requests from the same IP."""
        request = Mock(spec=["url", "method", "client", "headers", "state"])
        request.url = Mock()
        request.url.path = "/test"
        request.method = "GET"
        request.client = Mock()
        request.client.host = "192.168.1.100"
        request.headers = {}
        request.state = Mock()
        request.state.db = None

        import asyncio

        tasks = [middleware.dispatch(request, mock_call_next) for _ in range(3)]

        responses = await asyncio.gather(*tasks)
        assert all(response is not None for response in responses)

    async def test_api_key_hashing_consistency(
        self, middleware: RateLimitMiddleware, mock_call_next: AsyncMock
    ) -> None:
        """Test that API key hashing is consistent."""
        request1 = Mock(spec=["url", "method", "headers", "client", "state"])
        request1.url = Mock()
        request1.url.path = "/test"
        request1.method = "GET"
        request1.headers = {"Authorization": "Bearer test-key-123"}
        request1.client = None
        request1.state = Mock()
        request1.state.db = None

        request2 = Mock(spec=["url", "method", "headers", "client", "state"])
        request2.url = Mock()
        request2.url.path = "/test"
        request2.method = "GET"
        request2.headers = {"Authorization": "Bearer test-key-123"}
        request2.client = None
        request2.state = Mock()
        request2.state.db = None

        response1 = await middleware.dispatch(request1, mock_call_next)
        response2 = await middleware.dispatch(request2, mock_call_next)

        assert response1 is not None
        assert response2 is not None
        assert len(middleware.api_key_limits) == 1

    async def test_purge_stale_ip_entries(
        self, middleware: RateLimitMiddleware
    ) -> None:
        """Expired IP entries should be removed while active ones remain."""

        current_time = time.time()
        stale_entry = RateLimitEntry(window_size=60, max_requests=5)
        stale_entry.requests = [current_time - 4000]

        empty_entry = RateLimitEntry(window_size=60, max_requests=5)

        active_entry = RateLimitEntry(window_size=60, max_requests=5)
        active_entry.requests = [current_time - 30]

        blocked_entry = RateLimitEntry(window_size=60, max_requests=5)
        blocked_entry.blocked_until = current_time + 30
        blocked_entry.requests = [current_time - 5000]

        middleware.ip_limits = {
            "stale": stale_entry,
            "empty": empty_entry,
            "active": active_entry,
            "blocked": blocked_entry,
        }

        middleware._purge_stale_entries(current_time)

        assert "stale" not in middleware.ip_limits
        assert "empty" not in middleware.ip_limits
        assert "active" in middleware.ip_limits
        assert "blocked" in middleware.ip_limits

    async def test_purge_stale_api_key_entries(
        self, middleware: RateLimitMiddleware
    ) -> None:
        """Expired API key entries should be removed while active ones remain."""

        current_time = time.time()
        stale_key_entry = RateLimitEntry(window_size=60, max_requests=5)
        stale_key_entry.requests = [current_time - 5000]

        active_key_entry = RateLimitEntry(window_size=60, max_requests=5)
        active_key_entry.requests = [current_time - 10]

        middleware.api_key_limits = {
            "stale-key": stale_key_entry,
            "active-key": active_key_entry,
        }

        middleware._purge_stale_entries(current_time)

        assert "stale-key" not in middleware.api_key_limits
        assert "active-key" in middleware.api_key_limits
