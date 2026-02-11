"""Tests for application configuration."""

from __future__ import annotations

from app.config import Settings, settings


def test_default_settings() -> None:
    """Test that default settings are correctly set."""
    assert settings.app_name == "WireGuard Mesh Manager API"
    assert settings.app_version == "1.0.0"
    assert settings.service_name == "wireguard-mesh-manager"
    assert settings.debug is False
    assert settings.host == "0.0.0.0"
    assert settings.port == 8000


def test_settings_model() -> None:
    """Test that Settings model works correctly."""
    custom_settings = Settings(
        app_name="Custom API",
        debug=True,
        port=9000,
    )
    assert custom_settings.app_name == "Custom API"
    assert custom_settings.debug is True
    assert custom_settings.port == 9000
    assert custom_settings.service_name == "wireguard-mesh-manager"  # default value
