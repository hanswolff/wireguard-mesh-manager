"""Tests for CSRF protection middleware."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI, Request, status
from fastapi.testclient import TestClient
from starlette.responses import Response

from app.middleware.csrf import CSRFMiddleware, CSRFTokenStore


def build_request(
    method: str, path: str, headers: dict[str, str] | None = None
) -> Request:
    """Create a Request with properly formatted headers."""
    scope = {"type": "http", "method": method, "path": path, "headers": []}
    if headers:
        scope["headers"] = [  # type: ignore[misc]
            (key.lower().encode(), value.encode())  # type: ignore[misc]
            for key, value in headers.items()
        ]
    return Request(scope)


class TestCSRFTokenStore:
    """Test CSRF token storage functionality."""

    def test_add_and_validate_token(self) -> None:
        """Test adding and validating tokens."""
        store = CSRFTokenStore()
        token = "test_token"
        expires_at = datetime.now() + timedelta(hours=1)

        store.add_token(token, expires_at)
        assert store.is_valid(token) is True

    def test_expired_token_validation(self) -> None:
        """Test that expired tokens are not valid."""
        store = CSRFTokenStore()
        token = "expired_token"
        expires_at = datetime.now() - timedelta(minutes=1)

        store.add_token(token, expires_at)
        assert store.is_valid(token) is False

    def test_nonexistent_token_validation(self) -> None:
        """Test that nonexistent tokens are not valid."""
        store = CSRFTokenStore()
        assert store.is_valid("nonexistent") is False

    def test_cleanup_expired_tokens(self) -> None:
        """Test that expired tokens are cleaned up."""
        store = CSRFTokenStore()
        valid_token = "valid_token"
        expired_token = "expired_token"

        store.add_token(valid_token, datetime.now() + timedelta(hours=1))
        store.add_token(expired_token, datetime.now() - timedelta(minutes=1))

        # Should remove expired token but keep valid one
        assert store.is_valid(valid_token) is True
        assert store.is_valid(expired_token) is False
        assert expired_token not in store._tokens


class TestCSRFMiddleware:
    """Test CSRF middleware functionality."""

    @pytest.fixture
    def app(self) -> FastAPI:
        """Create a FastAPI app for testing."""
        app = FastAPI()

        @app.get("/test")
        async def test_get() -> dict:
            return {"message": "test"}

        @app.post("/test")
        async def test_post() -> dict:
            return {"message": "test post"}

        @app.post("/master-password/unlock")
        async def unlock() -> dict:
            return {"message": "unlock"}

        @app.get("/health")
        async def health() -> dict:
            return {"status": "ok"}

        return app

    @pytest.fixture
    def csrf_middleware(self) -> CSRFMiddleware:
        """Create CSRF middleware instance."""
        with patch("app.middleware.csrf.settings.csrf_protection_enabled", True):
            return CSRFMiddleware(FastAPI())

    def test_init_creates_token_store(self) -> None:
        """Test that middleware creates token store on init."""
        app = FastAPI()
        middleware = CSRFMiddleware(app)
        assert isinstance(middleware._token_store, CSRFTokenStore)

    @pytest.mark.asyncio
    async def test_dispatch_with_protection_disabled(self) -> None:
        """Test that requests pass through when protection is disabled."""
        app = FastAPI()

        @app.post("/test")
        async def test_endpoint() -> dict:
            return {"message": "test"}

        call_next = AsyncMock(return_value=Response(content='{"message": "test"}'))
        request = Request({"type": "http", "method": "POST", "path": "/test"})

        with patch("app.middleware.csrf.settings.csrf_protection_enabled", False):
            middleware = CSRFMiddleware(app)
            response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200
        call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_safe_methods_bypass_protection(self) -> None:
        """Test that safe HTTP methods bypass CSRF protection."""
        app = FastAPI()
        middleware = CSRFMiddleware(app)

        for method in ["GET", "HEAD", "OPTIONS", "TRACE"]:
            call_next = AsyncMock(return_value=Response())
            request = build_request(method, "/master-password/unlock")

            await middleware.dispatch(request, call_next)
            call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_exempt_paths_bypass_protection(self) -> None:
        """Test that exempt paths bypass CSRF protection."""
        app = FastAPI()
        middleware = CSRFMiddleware(app)

        exempt_paths = [
            "/health",
            "/ready",
            "/metrics",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/api/config/test",
            "/config/test",
            "/static/test.js",
            "/assets/style.css",
        ]

        for path in exempt_paths:
            call_next = AsyncMock(return_value=Response())
            request = build_request("POST", path)

            await middleware.dispatch(request, call_next)
            call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_protected_paths_require_csrf(self) -> None:
        """Test that protected paths require CSRF validation."""
        app = FastAPI()
        middleware = CSRFMiddleware(app)

        protected_paths = [
            "/master-password/unlock",
            "/networks",
            "/devices",
            "/api-keys",
        ]

        for path in protected_paths:
            call_next = AsyncMock(return_value=Response())
            request = build_request("POST", path)

            response = await middleware.dispatch(request, call_next)

            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert json.loads(response.body)["detail"] == "CSRF token missing"

    @pytest.mark.asyncio
    async def test_csrf_token_missing(self) -> None:
        """Test that missing CSRF token raises exception."""
        app = FastAPI()
        middleware = CSRFMiddleware(app)

        call_next = AsyncMock(return_value=Response())
        request = build_request("POST", "/master-password/unlock")

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert json.loads(response.body)["detail"] == "CSRF token missing"

    @pytest.mark.asyncio
    async def test_csrf_token_mismatch(self) -> None:
        """Test that mismatched CSRF tokens raise exception."""
        app = FastAPI()
        middleware = CSRFMiddleware(app)

        call_next = AsyncMock(return_value=Response())
        request = build_request(
            "POST",
            "/master-password/unlock",
            {
                "x-csrf-token": "header_token",
                "cookie": "csrf_token=cookie_token",
            },
        )

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert json.loads(response.body)["detail"] == "CSRF token mismatch"

    @pytest.mark.asyncio
    async def test_csrf_token_validation_success(self) -> None:
        """Test that matching valid CSRF tokens pass validation."""
        app = FastAPI()
        middleware = CSRFMiddleware(app)

        token = "valid_token"
        middleware._token_store.add_token(token, datetime.now() + timedelta(hours=1))

        call_next = AsyncMock(return_value=Response())
        request = build_request(
            "POST",
            "/master-password/unlock",
            {
                "x-csrf-token": token,
                "cookie": f"csrf_token={token}",
                "authorization": "Master test-token",
            },
        )

        await middleware.dispatch(request, call_next)
        call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_origin_validation_success(self) -> None:
        """Test that valid origins pass validation."""
        app = FastAPI()
        middleware = CSRFMiddleware(app)

        token = "valid_token"
        middleware._token_store.add_token(token, datetime.now() + timedelta(hours=1))

        with patch(
            "app.middleware.csrf.settings.cors_origins", "http://localhost:3000"
        ):
            call_next = AsyncMock(return_value=Response())
            request = build_request(
                "POST",
                "/master-password/unlock",
                {
                    "x-csrf-token": token,
                    "cookie": f"csrf_token={token}",
                    "origin": "http://localhost:3000",
                },
            )

            await middleware.dispatch(request, call_next)
            call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_origin_raises_exception(self) -> None:
        """Test that invalid origins raise exception."""
        app = FastAPI()
        middleware = CSRFMiddleware(app)

        token = "valid_token"
        middleware._token_store.add_token(token, datetime.now() + timedelta(hours=1))

        with patch(
            "app.middleware.csrf.settings.cors_origins", "http://localhost:3000"
        ):
            call_next = AsyncMock(return_value=Response())
            request = build_request(
                "POST",
                "/master-password/unlock",
                {
                    "x-csrf-token": token,
                    "cookie": f"csrf_token={token}",
                    "origin": "http://evil.com",
                },
            )

            response = await middleware.dispatch(request, call_next)

            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert json.loads(response.body)["detail"] == "Origin validation failed"

    @pytest.mark.asyncio
    async def test_subdomain_wildcard_matching(self) -> None:
        """Test that subdomain wildcard matching works."""
        app = FastAPI()
        middleware = CSRFMiddleware(app)

        token = "valid_token"
        middleware._token_store.add_token(token, datetime.now() + timedelta(hours=1))

        with patch("app.middleware.csrf.settings.cors_origins", "*.example.com"):
            call_next = AsyncMock(return_value=Response())
            request = build_request(
                "POST",
                "/master-password/unlock",
                {
                    "x-csrf-token": token,
                    "cookie": f"csrf_token={token}",
                    "origin": "https://admin.example.com",
                },
            )

            await middleware.dispatch(request, call_next)
            call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_sets_cookie_for_html_responses(self) -> None:
        """Test that CSRF cookie is set for HTML responses."""
        app = FastAPI()
        middleware = CSRFMiddleware(app)

        call_next = AsyncMock(
            return_value=Response(
                content="<html></html>", headers={"content-type": "text/html"}
            )
        )
        request = build_request("GET", "/test")

        response = await middleware.dispatch(request, call_next)

        # Check that cookie was set
        cookies = response.headers.get("set-cookie")
        assert cookies is not None
        assert "csrf_token=" in cookies

    @pytest.mark.asyncio
    async def test_sets_cookie_for_ajax_requests(self) -> None:
        """Test that CSRF cookie is set for AJAX requests."""
        app = FastAPI()
        middleware = CSRFMiddleware(app)

        call_next = AsyncMock(
            return_value=Response(
                content='{"message": "test"}',
                headers={"content-type": "application/json"},
            )
        )
        request = build_request(
            "GET",
            "/test",
            {"x-requested-with": "XMLHttpRequest"},
        )

        response = await middleware.dispatch(request, call_next)

        # Check that cookie was set
        cookies = response.headers.get("set-cookie")
        assert cookies is not None
        assert "csrf_token=" in cookies

    @pytest.mark.asyncio
    async def test_does_not_set_cookie_for_api_responses(self) -> None:
        """Test that CSRF cookie is not set for regular API responses."""
        app = FastAPI()
        middleware = CSRFMiddleware(app)

        call_next = AsyncMock(
            return_value=Response(
                content='{"message": "test"}',
                headers={"content-type": "application/json"},
            )
        )
        request = build_request("GET", "/test")

        response = await middleware.dispatch(request, call_next)

        # Check that cookie was not set
        cookies = response.headers.get("set-cookie")
        assert cookies is None

    def test_should_skip_protection_logic(self) -> None:
        """Test the _should_skip_protection helper method logic."""
        app = FastAPI()
        middleware = CSRFMiddleware(app)

        # Test safe method
        request = build_request("GET", "/master-password/unlock")
        assert (
            middleware._should_skip_protection(request, "/master-password/unlock")
            is True
        )

        # Test exempt path
        request = build_request("POST", "/health")
        assert middleware._should_skip_protection(request, "/health") is True

        # Test protected path with unsafe method
        request = build_request("POST", "/master-password/unlock")
        assert (
            middleware._should_skip_protection(request, "/master-password/unlock")
            is False
        )

    @pytest.mark.asyncio
    async def test_integration_with_fastapi_client(self) -> None:
        """Test middleware integration with FastAPI test client."""
        app = FastAPI()

        @app.post("/master-password/unlock")
        async def protected_endpoint() -> dict:
            return {"message": "protected"}

        # Add CSRF middleware
        app.add_middleware(CSRFMiddleware)

        client = TestClient(app, raise_server_exceptions=False)

        # Request without CSRF token should fail
        response = client.post("/master-password/unlock")
        assert response.status_code == 403

        # GET request should succeed and set cookie
        response = client.get("/")
        assert (
            response.status_code == 404
        )  # 404 because no route defined, but middleware should not block

        # Note: Full integration testing with actual CSRF tokens would require
        # more complex setup with proper cookie handling
