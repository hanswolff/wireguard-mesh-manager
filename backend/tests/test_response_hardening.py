"""Tests for response hardening middleware."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.testclient import TestClient
from starlette.responses import Response

from app.middleware.response_hardening import (
    ResponseHardeningMiddleware,
    add_response_hardening_middleware,
)


class TestResponseHardeningMiddleware:
    """Test cases for ResponseHardeningMiddleware."""

    @pytest.fixture
    def app(self) -> FastAPI:
        """Create a test FastAPI app for testing."""
        app = FastAPI()

        @app.get("/")
        async def root() -> JSONResponse:
            return JSONResponse({"message": "test"})

        @app.get("/config")
        async def config() -> PlainTextResponse:
            return PlainTextResponse("[Interface]\nAddress = 10.0.0.1/24")

        @app.get("/api/test")
        async def api_test() -> JSONResponse:
            return JSONResponse({"data": "api_response"})

        @app.post("/sensitive")
        async def sensitive() -> JSONResponse:
            return JSONResponse({"private_data": "sensitive_data"})

        @app.get("/web-page")
        async def web_page() -> Response:
            return Response(
                content="<html><body>Test</body></html>", media_type="text/html"
            )

        @app.get("/api/devices/123/config")
        async def api_config() -> PlainTextResponse:
            return PlainTextResponse("[Interface]\nAddress = 10.0.0.2/24")

        @app.get("/api/devices/123/config-json")
        async def api_config_json() -> JSONResponse:
            return JSONResponse({"config": "json"})

        @app.get("/api/api-keys")
        async def api_keys() -> JSONResponse:
            return JSONResponse({"keys": []})

        @app.post("/master-password/unlock")
        async def master_unlock() -> JSONResponse:
            return JSONResponse({"token": "test"})

        @app.get("/api/export")
        async def export() -> JSONResponse:
            return JSONResponse({"export": "data"})

        @app.post("/api/devices")
        async def create_device() -> JSONResponse:
            return JSONResponse({"id": "new_device"})

        @app.get("/api/health")
        async def health() -> JSONResponse:
            return JSONResponse({"status": "healthy"})

        add_response_hardening_middleware(app)
        return app

    @pytest.fixture
    def client(self, app: FastAPI) -> TestClient:
        """Create a test client."""
        return TestClient(app)

    def test_security_headers_added_to_all_responses(self, client: TestClient) -> None:
        """Test that security headers are added to all responses."""
        response = client.get("/")

        assert response.status_code == 200
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert response.headers["Server"] == ""

    def test_sensitive_endpoint_cache_control(self, client: TestClient) -> None:
        """Test that sensitive endpoints have strict cache control."""
        response = client.get("/config")

        assert response.status_code == 200
        assert (
            response.headers["Cache-Control"]
            == "no-cache, no-store, must-revalidate, private"
        )
        assert response.headers["Pragma"] == "no-cache"
        assert response.headers["Expires"] == "0"
        assert response.headers["Vary"] == "Accept-Encoding, Cookie, Authorization"

    def test_api_endpoint_cache_control(self, client: TestClient) -> None:
        """Test that API endpoints have conservative cache control."""
        response = client.get("/api/test")

        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-cache, must-revalidate, private"
        assert response.headers["Vary"] == "Accept-Encoding, Cookie, Authorization"

    def test_sensitive_post_endpoint_cache_control(self, client: TestClient) -> None:
        """Test that POST endpoints to sensitive data have strict cache control."""
        response = client.post("/sensitive")

        assert response.status_code == 200
        assert (
            response.headers["Cache-Control"]
            == "no-cache, no-store, must-revalidate, private"
        )

    def test_config_endpoint_content_type_enforcement(self, client: TestClient) -> None:
        """Test that config endpoints have proper content type enforcement."""
        response = client.get("/config")

        assert response.status_code == 200
        assert response.headers["Content-Type"] == "text/plain; charset=utf-8"
        # Content-Disposition is set by the middleware if missing, but our test endpoint provides one
        assert "Content-Disposition" in response.headers

    def test_json_config_endpoint_preserves_json_content_type(
        self, client: TestClient
    ) -> None:
        """Test that JSON config endpoints keep application/json content type."""
        response = client.get("/api/devices/123/config-json")

        assert response.status_code == 200
        assert response.headers["Content-Type"].startswith("application/json")

    def test_csp_not_added_to_api_endpoints(self, client: TestClient) -> None:
        """Test that CSP is not added to API endpoints."""
        response = client.get("/api/test")

        assert response.status_code == 200
        assert "Content-Security-Policy" not in response.headers

    def test_csp_not_added_to_config_endpoints(self, client: TestClient) -> None:
        """Test that CSP is not added to config download endpoints."""
        response = client.get("/config")

        assert response.status_code == 200
        assert "Content-Security-Policy" not in response.headers

    def test_csp_added_to_web_endpoints(self, client: TestClient) -> None:
        """Test that CSP is added to non-API, non-config endpoints."""
        response = client.get("/web-page")

        assert response.status_code == 200
        assert "Content-Security-Policy" in response.headers
        csp = response.headers["Content-Security-Policy"]
        assert "default-src 'none'" in csp
        assert "script-src 'none'" in csp
        assert "frame-ancestors 'none'" in csp

    def test_is_sensitive_endpoint_detection(self) -> None:
        """Test the sensitive endpoint detection logic."""
        middleware = ResponseHardeningMiddleware(app=FastAPI())

        # Test with direct calls using path matching
        assert (
            middleware._is_sensitive_endpoint(
                type(
                    "MockRequest",
                    (),
                    {"url": type("MockURL", (), {"path": "/api/devices/123/config"})()},
                )()
            )
            is True
        )
        assert (
            middleware._is_sensitive_endpoint(
                type(
                    "MockRequest",
                    (),
                    {"url": type("MockURL", (), {"path": "/api/api-keys"})()},
                )()
            )
            is True
        )
        assert (
            middleware._is_sensitive_endpoint(
                type(
                    "MockRequest",
                    (),
                    {"url": type("MockURL", (), {"path": "/master-password/unlock"})()},
                )()
            )
            is True
        )
        assert (
            middleware._is_sensitive_endpoint(
                type(
                    "MockRequest",
                    (),
                    {"url": type("MockURL", (), {"path": "/api/export"})()},
                )()
            )
            is True
        )

        # Create mock request for POST method
        post_request = type(
            "MockRequest",
            (),
            {"url": type("MockURL", (), {"path": "/api/devices"})(), "method": "POST"},
        )()
        assert middleware._is_sensitive_endpoint(post_request) is True

        # Test non-sensitive endpoint
        get_request = type(
            "MockRequest",
            (),
            {"url": type("MockURL", (), {"path": "/api/health"})(), "method": "GET"},
        )()
        assert middleware._is_sensitive_endpoint(get_request) is False

    def test_is_api_endpoint_detection(self) -> None:
        """Test the API endpoint detection logic."""
        middleware = ResponseHardeningMiddleware(app=FastAPI())

        # Test with direct calls using path matching
        assert (
            middleware._is_api_endpoint(
                type(
                    "MockRequest",
                    (),
                    {"url": type("MockURL", (), {"path": "/api/test"})()},
                )()
            )
            is True
        )
        assert (
            middleware._is_api_endpoint(
                type(
                    "MockRequest",
                    (),
                    {"url": type("MockURL", (), {"path": "/api/devices"})()},
                )()
            )
            is True
        )
        assert (
            middleware._is_api_endpoint(
                type(
                    "MockRequest", (), {"url": type("MockURL", (), {"path": "/docs"})()}
                )()
            )
            is False
        )
        assert (
            middleware._is_api_endpoint(
                type(
                    "MockRequest",
                    (),
                    {"url": type("MockURL", (), {"path": "/api/devices/123/config"})()},
                )()
            )
            is True
        )

    def test_needs_csp_detection(self) -> None:
        """Test the CSP detection logic."""
        middleware = ResponseHardeningMiddleware(app=FastAPI())

        # Test with direct calls using path matching
        assert (
            middleware._needs_content_security_policy(
                type(
                    "MockRequest",
                    (),
                    {"url": type("MockURL", (), {"path": "/api/test"})()},
                )()
            )
            is False
        )
        assert (
            middleware._needs_content_security_policy(
                type(
                    "MockRequest",
                    (),
                    {"url": type("MockURL", (), {"path": "/api/devices"})()},
                )()
            )
            is False
        )
        assert (
            middleware._needs_content_security_policy(
                type(
                    "MockRequest",
                    (),
                    {"url": type("MockURL", (), {"path": "/api/devices/123/config"})()},
                )()
            )
            is False
        )
        assert (
            middleware._needs_content_security_policy(
                type(
                    "MockRequest", (), {"url": type("MockURL", (), {"path": "/docs"})()}
                )()
            )
            is True
        )
        assert (
            middleware._needs_content_security_policy(
                type(
                    "MockRequest",
                    (),
                    {"url": type("MockURL", (), {"path": "/some/config/download"})()},
                )()
            )
            is False
        )

    def test_enforce_content_type_for_config(self, client: TestClient) -> None:
        """Test content type enforcement for config endpoints."""
        response = client.get("/config")

        assert response.status_code == 200
        assert response.headers["Content-Type"] == "text/plain; charset=utf-8"
        # Content-Disposition should be present for config endpoints
        assert "Content-Disposition" in response.headers

    def test_middleware_preserves_response_content(self, client: TestClient) -> None:
        """Test that middleware doesn't alter response content."""
        # Test JSON response
        response = client.get("/")
        assert response.json() == {"message": "test"}

        # Test plain text response
        response = client.get("/config")
        assert "[Interface]" in response.text
        assert "Address = 10.0.0.1/24" in response.text

    def test_vary_header_for_sensitive_endpoints(self, client: TestClient) -> None:
        """Test that Vary header includes authorization for sensitive endpoints."""
        response = client.get("/config")

        assert response.status_code == 200
        vary_header = response.headers["Vary"]
        assert "Accept-Encoding" in vary_header
        assert "Cookie" in vary_header
        assert "Authorization" in vary_header
