"""Tests for CSRF router endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


class TestCSRFRouter:
    """Test CSRF router endpoints."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client."""
        return TestClient(app)

    def test_get_csrf_token_endpoint(self, client) -> None:
        """Test CSRF token endpoint returns expected response."""
        response = client.get("/api/csrf/token")

        assert response.status_code == 200
        data = response.json()
        assert "csrf_token" in data
        assert (
            data["csrf_token"] == "Token set in cookie - read from X-CSRF-Token header"
        )

    def test_get_csrf_token_sets_cookie(self, client) -> None:
        """Test that CSRF token endpoint sets CSRF cookie."""
        response = client.get("/api/csrf/token")

        assert response.status_code == 200

        # Check that cookie was set
        set_cookie_header = response.headers.get("set-cookie")
        assert set_cookie_header is not None
        assert "csrf_token=" in set_cookie_header

    def test_csrf_cookie_security_attributes(self, client) -> None:
        """Test that CSRF cookie has correct security attributes."""
        response = client.get("/api/csrf/token")

        assert response.status_code == 200

        set_cookie_header = response.headers.get("set-cookie")
        assert set_cookie_header is not None

        # Check for security flags
        assert (
            "HttpOnly" not in set_cookie_header
        )  # Should be False for JavaScript access
        assert "SameSite=strict" in set_cookie_header
        # In test environment (http), secure should not be set
        assert "Secure" not in set_cookie_header

    def test_get_security_settings_endpoint(self, client) -> None:
        """Test security settings endpoint returns expected structure."""
        response = client.get("/api/csrf/settings")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        expected_fields = [
            "cors_origins",
            "csrf_protection_enabled",
            "trusted_proxies",
            "security_headers",
        ]
        for field in expected_fields:
            assert field in data

        # Verify security headers structure
        headers = data["security_headers"]
        expected_header_fields = [
            "contentTypeOptions",
            "frameOptions",
            "xssProtection",
            "referrerPolicy",
            "contentSecurityPolicy",
        ]
        for field in expected_header_fields:
            assert field in headers

    def test_security_headers_values(self, client) -> None:
        """Test that security headers have expected values."""
        response = client.get("/api/csrf/settings")

        assert response.status_code == 200
        data = response.json()
        headers = data["security_headers"]

        assert headers["contentTypeOptions"] == "nosniff"
        assert headers["frameOptions"] == "DENY"
        assert headers["xssProtection"] == "1; mode=block"
        assert headers["referrerPolicy"] == "strict-origin-when-cross-origin"
        assert "default-src 'self'" in headers["contentSecurityPolicy"]
        assert "script-src 'self' 'unsafe-inline'" in headers["contentSecurityPolicy"]
        assert "style-src 'self' 'unsafe-inline'" in headers["contentSecurityPolicy"]

    def test_security_settings_reflects_config(self, client) -> None:
        """Test that security settings reflect actual configuration."""
        response = client.get("/api/csrf/settings")

        assert response.status_code == 200
        data = response.json()

        # CSRF protection should be enabled by default
        assert data["csrf_protection_enabled"] is True

        # Should have default CORS origins
        assert "http://localhost:3000" in data["cors_origins"]

    def test_csrf_router_tags(self) -> None:
        """Test that CSRF router has correct tags."""
        from app.routers.csrf import router

        assert "csrf" in router.tags

    def test_csrf_router_prefix(self) -> None:
        """Test that CSRF router has correct prefix."""
        from app.routers.csrf import router

        # Router itself has no prefix, prefix is added in main.py via include_router
        assert router.prefix == ""

    def test_multiple_csrf_token_requests(self, client) -> None:
        """Test multiple requests to CSRF token endpoint."""
        # First request
        response1 = client.get("/api/csrf/token")
        assert response1.status_code == 200

        cookie1 = response1.headers.get("set-cookie")

        # Second request
        response2 = client.get("/api/csrf/token")
        assert response2.status_code == 200

        cookie2 = response2.headers.get("set-cookie")

        # Both should set cookies
        assert cookie1 is not None
        assert cookie2 is not None
        assert "csrf_token=" in cookie1
        assert "csrf_token=" in cookie2

    def test_security_settings_cors_origins_format(self, client) -> None:
        """Test that CORS origins are returned in expected format."""
        response = client.get("/api/csrf/settings")

        assert response.status_code == 200
        data = response.json()

        # Should be a string that can be split by commas
        assert isinstance(data["cors_origins"], str)

        # Should contain at least one origin
        origins = [o.strip() for o in data["cors_origins"].split(",") if o.strip()]
        assert len(origins) > 0

    def test_security_settings_trusted_proxies_display(self, client) -> None:
        """Test trusted proxies display format."""
        response = client.get("/api/csrf/settings")

        assert response.status_code == 200
        data = response.json()

        # Should either have actual proxies or a default message
        if not data["trusted_proxies"]:
            assert data["trusted_proxies"] == "None configured (deny-by-default)"
        else:
            assert isinstance(data["trusted_proxies"], str)
