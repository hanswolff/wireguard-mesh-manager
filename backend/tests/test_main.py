"""Tests for the main FastAPI application."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)


def test_root_endpoint() -> None:
    """Test the root endpoint returns the expected message."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": settings.app_name}
    assert response.headers["content-type"] == "application/json"


def test_health_check_endpoint() -> None:
    """Test the health check endpoint returns healthy status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "unhealthy"]
    assert data["service"] == settings.service_name
    assert data["version"] == settings.app_version
    assert "timestamp" in data
    assert "uptime_seconds" in data
    assert "database_status" in data
    assert response.headers["content-type"] == "application/json"


def test_health_check_response_structure() -> None:
    """Test the health check endpoint has the correct response structure."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "status" in data
    assert "service" in data
    assert "version" in data
    assert "timestamp" in data
    assert "uptime_seconds" in data
    assert "database_status" in data


def test_docs_endpoint_available() -> None:
    """Test that the OpenAPI docs endpoint is available."""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_redoc_endpoint_available() -> None:
    """Test that the ReDoc endpoint is available."""
    response = client.get("/redoc")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_openapi_endpoint_available() -> None:
    """Test that the OpenAPI JSON endpoint is available."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    data = response.json()
    assert "openapi" in data
    assert "info" in data
    assert data["info"]["title"] == settings.app_name


def test_app_configuration() -> None:
    """Test that the app is configured with correct settings."""
    assert app.title == settings.app_name
    assert app.version == settings.app_version
    assert app.docs_url == "/docs"
    assert app.redoc_url == "/redoc"
