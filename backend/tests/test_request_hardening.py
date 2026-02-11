"""Tests for request hardening middleware."""

from __future__ import annotations

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.config import settings
from app.middleware.request_hardening import (
    RequestSizeMiddleware,
    RequestTimeoutMiddleware,
    StrictJSONMiddleware,
)


@pytest.fixture
def app():
    """Create a FastAPI app for testing."""
    app = FastAPI()

    @app.post("/test")
    async def test_endpoint(request: Request) -> dict:
        try:
            body = await request.json()
            return {"received": body}
        except Exception:
            # Handle empty body case
            return {"received": None}

    @app.get("/test")
    async def test_get_endpoint() -> dict:
        return {"message": "test"}

    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    # Add middleware to the app
    app.add_middleware(RequestSizeMiddleware)
    app.add_middleware(RequestTimeoutMiddleware)
    app.add_middleware(StrictJSONMiddleware)
    return TestClient(app)


class TestRequestSizeMiddleware:
    """Test request size limiting middleware."""

    def test_request_within_size_limit(self, client):
        """Test that requests within size limit are allowed."""
        small_data = {"test": "data"}
        response = client.post("/test", json=small_data)
        assert response.status_code == 200
        assert response.json() == {"received": small_data}

    def test_request_exceeding_size_limit(self, client):
        """Test that requests exceeding size limit are rejected."""
        # Create a large payload that exceeds the limit
        large_data = {"data": "x" * (settings.max_request_size + 1000)}
        response = client.post("/test", json=large_data)
        assert response.status_code == 413
        assert response.json()["error"] == "request_too_large"
        assert "Maximum size" in response.json()["message"]

    def test_request_with_content_length_header_too_large(self, client):
        """Test rejection via content-length header."""
        large_data = {"data": "x" * 1000}
        response = client.post(
            "/test",
            json=large_data,
            headers={"content-length": str(settings.max_request_size + 1)},
        )
        assert response.status_code == 413


class TestStrictJSONMiddleware:
    """Test strict JSON validation middleware."""

    def test_valid_json(self, client):
        """Test that valid JSON is accepted."""
        valid_data = {"name": "test", "value": 123, "nested": {"key": "value"}}
        response = client.post("/test", json=valid_data)
        assert response.status_code == 200
        assert response.json() == {"received": valid_data}

    def test_invalid_json(self, client):
        """Test that invalid JSON is rejected."""
        invalid_json = '{"name": "test", invalid}'
        response = client.post(
            "/test",
            content=invalid_json,
            headers={"content-type": "application/json"},
        )
        assert response.status_code == 400
        assert response.json()["error"] == "invalid_json"

    def test_json_with_string_too_long(self, client):
        """Test rejection of JSON with strings exceeding max length."""
        long_string = "x" * (settings.max_string_length + 1)
        data = {"long_string": long_string}
        response = client.post("/test", json=data)
        assert response.status_code == 422
        assert response.json()["error"] == "json_validation_error"
        details = response.json()["details"]
        assert any("String too long" in error for error in details)

    def test_json_with_array_too_large(self, client):
        """Test rejection of JSON with arrays exceeding max items."""
        large_array = list(range(settings.max_items_per_array + 1))
        data = {"large_array": large_array}
        response = client.post("/test", json=data)
        assert response.status_code == 422
        assert response.json()["error"] == "json_validation_error"
        details = response.json()["details"]
        assert any("Array too large" in error for error in details)

    def test_json_with_excessive_nesting(self, client):
        """Test rejection of JSON with excessive nesting depth."""
        # Create deeply nested object
        nested = {}
        current = nested
        for _i in range(settings.max_json_depth + 1):
            current["level"] = {}
            current = current["level"]

        data = {"nested": nested}
        response = client.post("/test", json=data)
        assert response.status_code == 422
        assert response.json()["error"] == "json_validation_error"
        details = response.json()["details"]
        assert any("Maximum JSON depth" in error for error in details)

    def test_non_json_request_ignored(self, client):
        """Test that non-JSON requests are not validated."""
        response = client.get("/test")
        assert response.status_code == 200
        assert response.json() == {"message": "test"}

    def test_empty_json_body(self, client):
        """Test that empty JSON body is handled correctly."""
        response = client.post(
            "/test", content="", headers={"content-type": "application/json"}
        )
        # Empty body should pass through our middleware and be handled by the endpoint
        assert response.status_code == 200
        assert response.json() == {"received": None}


class TestRequestTimeoutMiddleware:
    """Test request timeout monitoring middleware."""

    def test_processing_time_header_added(self, client):
        """Test that processing time header is added."""
        response = client.get("/test")
        assert response.status_code == 200
        assert "x-process-time" in response.headers
        # Should be a float representing seconds
        processing_time = float(response.headers["x-process-time"])
        assert processing_time >= 0


class TestMiddlewareIntegration:
    """Test middleware integration and order."""

    def test_middleware_chain_order(self, client):
        """Test that middleware executes in the correct order."""
        # This test ensures that all middleware work together
        data = {"test": "integration"}
        response = client.post("/test", json=data)

        # Should succeed with valid, properly-sized data
        assert response.status_code == 200
        assert response.json() == {"received": data}

        # Should have processing time header
        assert "x-process-time" in response.headers

    def test_size_middleware_takes_precedence(self, client):
        """Test that size checking happens before JSON validation."""
        # This should be caught by size middleware, not JSON validation
        response = client.post(
            "/test",
            content="x" * (settings.max_request_size + 1000),
            headers={"content-type": "application/json"},
        )
        assert response.status_code == 413
        assert response.json()["error"] == "request_too_large"
