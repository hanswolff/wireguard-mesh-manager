"""Tests for operational settings endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_operational_settings(async_client: AsyncClient) -> None:
    """Test getting operational settings."""
    response = await async_client.get("/api/settings")
    assert response.status_code == 200

    data = response.json()
    # Verify all required fields are present
    required_fields = [
        "max_request_size",
        "request_timeout",
        "max_json_depth",
        "max_string_length",
        "max_items_per_array",
        "rate_limit_api_key_window",
        "rate_limit_api_key_max_requests",
        "rate_limit_ip_window",
        "rate_limit_ip_max_requests",
        "audit_retention_days",
        "audit_export_batch_size",
        "master_password_ttl_hours",
        "master_password_idle_timeout_minutes",
        "master_password_per_user_session",
        "trusted_proxies",
        "cors_origins",
        "cors_allow_credentials",
        "logo_bg_color",
        "logo_text",
        "app_name",
    ]
    for field in required_fields:
        assert field in data, f"Missing field: {field}"


@pytest.mark.asyncio
async def test_default_logo_settings(async_client: AsyncClient) -> None:
    """Test that default logo settings values are correct."""
    # This test assumes a fresh database where no logo settings exist
    # The defaults are defined in get_settings_from_db

    # Get current settings (should return defaults if not in DB)
    response = await async_client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()

    # Verify default logo background color is dark blue
    assert data["logo_bg_color"] == "#1e3a8a"

    # Verify default logo text is WG
    assert data["logo_text"] == "WG"

    # Verify default app name is WireGuard Mesh Manager
    assert data["app_name"] == "WireGuard Mesh Manager"


@pytest.mark.asyncio
async def test_update_operational_settings_single_field(
    async_client: AsyncClient,
) -> None:
    """Test updating a single setting field."""
    # Get current settings
    get_response = await async_client.get("/api/settings")
    assert get_response.status_code == 200
    current_data = get_response.json()

    # Update max_request_size
    update_data = {"max_request_size": 2097152}  # 2MB
    response = await async_client.patch("/api/settings", json=update_data)
    assert response.status_code == 200

    # Verify update
    updated_data = response.json()
    assert updated_data["max_request_size"] == 2097152

    # Restore original value
    restore_data = {"max_request_size": current_data["max_request_size"]}
    await async_client.patch("/api/settings", json=restore_data)


@pytest.mark.asyncio
async def test_update_operational_settings_multiple_fields(
    async_client: AsyncClient,
) -> None:
    """Test updating multiple settings fields."""
    # Get current settings
    get_response = await async_client.get("/api/settings")
    assert get_response.status_code == 200
    current_data = get_response.json()

    # Update multiple fields
    update_data = {
        "request_timeout": 45,
        "max_json_depth": 15,
        "trusted_proxies": "127.0.0.1, ::1",
    }
    response = await async_client.patch("/api/settings", json=update_data)
    assert response.status_code == 200

    # Verify updates
    updated_data = response.json()
    assert updated_data["request_timeout"] == 45
    assert updated_data["max_json_depth"] == 15
    assert updated_data["trusted_proxies"] == "127.0.0.1, ::1"

    # Restore original values
    restore_data = {
        "request_timeout": current_data["request_timeout"],
        "max_json_depth": current_data["max_json_depth"],
        "trusted_proxies": current_data["trusted_proxies"],
    }
    await async_client.patch("/api/settings", json=restore_data)


@pytest.mark.asyncio
async def test_update_empty_payload_rejected(
    async_client: AsyncClient,
) -> None:
    """Test that empty update payload is rejected."""
    response = await async_client.patch("/api/settings", json={})
    assert response.status_code == 400

    data = response.json()
    assert "No fields provided for update" in str(data.get("detail", ""))


@pytest.mark.asyncio
async def test_update_invalid_max_request_size(async_client: AsyncClient) -> None:
    """Test validation for max_request_size field."""
    # Test value too small
    response = await async_client.patch(
        "/api/settings", json={"max_request_size": 100}
    )
    assert response.status_code == 422

    # Test value too large
    response = await async_client.patch(
        "/api/settings", json={"max_request_size": 200000000}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_invalid_request_timeout(async_client: AsyncClient) -> None:
    """Test validation for request_timeout field."""
    # Test value too small
    response = await async_client.patch(
        "/api/settings", json={"request_timeout": 0}
    )
    assert response.status_code == 422

    # Test value too large
    response = await async_client.patch(
        "/api/settings", json={"request_timeout": 500}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_invalid_max_json_depth(async_client: AsyncClient) -> None:
    """Test validation for max_json_depth field."""
    # Test value too small
    response = await async_client.patch(
        "/api/settings", json={"max_json_depth": 0}
    )
    assert response.status_code == 422

    # Test value too large
    response = await async_client.patch(
        "/api/settings", json={"max_json_depth": 200}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_invalid_trusted_proxies(async_client: AsyncClient) -> None:
    """Test validation for trusted_proxies field."""
    # Test invalid IP format
    response = await async_client.patch(
        "/api/settings", json={"trusted_proxies": "invalid-ip, 127.0.0.1"}
    )
    assert response.status_code == 422

    # Test valid IPs
    response = await async_client.patch(
        "/api/settings", json={"trusted_proxies": "127.0.0.1, 10.0.0.0/8, ::1"}
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_update_invalid_cors_origins(async_client: AsyncClient) -> None:
    """Test validation for cors_origins field."""
    # Test invalid URL format
    response = await async_client.patch(
        "/api/settings", json={"cors_origins": "invalid-url"}
    )
    assert response.status_code == 422

    # Test valid URLs
    response = await async_client.patch(
        "/api/settings",
        json={
            "cors_origins": "http://localhost:3000,https://example.com"
        },
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_update_invalid_rate_limit_fields(async_client: AsyncClient) -> None:
    """Test validation for rate limiting fields."""
    # Test rate_limit_api_key_window too large
    response = await async_client.patch(
        "/api/settings", json={"rate_limit_api_key_window": 100000}
    )
    assert response.status_code == 422

    # Test rate_limit_api_key_max_requests too small
    response = await async_client.patch(
        "/api/settings", json={"rate_limit_api_key_max_requests": 0}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_invalid_audit_settings(async_client: AsyncClient) -> None:
    """Test validation for audit settings."""
    # Test audit_retention_days too large
    response = await async_client.patch(
        "/api/settings", json={"audit_retention_days": 4000}
    )
    assert response.status_code == 422

    # Test audit_export_batch_size too small
    response = await async_client.patch(
        "/api/settings", json={"audit_export_batch_size": 50}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_invalid_master_password_settings(
    async_client: AsyncClient,
) -> None:
    """Test validation for master password cache settings."""
    # Test master_password_ttl_hours too large
    response = await async_client.patch(
        "/api/settings", json={"master_password_ttl_hours": 30.0}
    )
    assert response.status_code == 422

    # Test master_password_idle_timeout_minutes too small
    response = await async_client.patch(
        "/api/settings", json={"master_password_idle_timeout_minutes": 0.5}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_persists_to_database(async_client: AsyncClient) -> None:
    """Test that updates persist to database."""
    # Update a setting
    update_data = {"request_timeout": 60}
    response = await async_client.patch("/api/settings", json=update_data)
    assert response.status_code == 200

    # Get settings again to verify persistence
    get_response = await async_client.get("/api/settings")
    assert get_response.status_code == 200
    data = get_response.json()
    assert data["request_timeout"] == 60

    # Restore original
    restore_data = {"request_timeout": 30}
    await async_client.patch("/api/settings", json=restore_data)


@pytest.mark.asyncio
async def test_update_logo_bg_color(async_client: AsyncClient) -> None:
    """Test updating logo background color."""
    # Get current settings
    get_response = await async_client.get("/api/settings")
    assert get_response.status_code == 200
    current_data = get_response.json()

    # Update logo_bg_color with valid hex color (6 characters)
    update_data = {"logo_bg_color": "#FF5733"}
    response = await async_client.patch("/api/settings", json=update_data)
    assert response.status_code == 200

    # Verify update
    updated_data = response.json()
    assert updated_data["logo_bg_color"] == "#FF5733"

    # Test 3-character hex color
    response = await async_client.patch("/api/settings", json={"logo_bg_color": "#F53"})
    assert response.status_code == 200
    assert response.json()["logo_bg_color"] == "#F53"

    # Test 8-character hex color (with alpha)
    response = await async_client.patch("/api/settings", json={"logo_bg_color": "#FF5733AA"})
    assert response.status_code == 200
    assert response.json()["logo_bg_color"] == "#FF5733AA"

    # Restore original value
    restore_data = {"logo_bg_color": current_data["logo_bg_color"]}
    await async_client.patch("/api/settings", json=restore_data)


@pytest.mark.asyncio
async def test_update_logo_text(async_client: AsyncClient) -> None:
    """Test updating logo text."""
    # Get current settings
    get_response = await async_client.get("/api/settings")
    assert get_response.status_code == 200
    current_data = get_response.json()

    # Update logo_text with valid 3-character text
    update_data = {"logo_text": "XYZ"}
    response = await async_client.patch("/api/settings", json=update_data)
    assert response.status_code == 200

    # Verify update
    updated_data = response.json()
    assert updated_data["logo_text"] == "XYZ"

    # Test 2-character text
    response = await async_client.patch("/api/settings", json={"logo_text": "AB"})
    assert response.status_code == 200
    assert response.json()["logo_text"] == "AB"

    # Test 1-character text
    response = await async_client.patch("/api/settings", json={"logo_text": "W"})
    assert response.status_code == 200
    assert response.json()["logo_text"] == "W"

    # Restore original value
    restore_data = {"logo_text": current_data["logo_text"]}
    await async_client.patch("/api/settings", json=restore_data)


@pytest.mark.asyncio
async def test_update_app_name(async_client: AsyncClient) -> None:
    """Test updating app name."""
    # Get current settings
    get_response = await async_client.get("/api/settings")
    assert get_response.status_code == 200
    current_data = get_response.json()

    # Update app_name with valid text
    update_data = {"app_name": "My Custom App"}
    response = await async_client.patch("/api/settings", json=update_data)
    assert response.status_code == 200

    # Verify update
    updated_data = response.json()
    assert updated_data["app_name"] == "My Custom App"

    # Test with default value
    response = await async_client.patch("/api/settings", json={"app_name": "WireGuard Mesh Manager"})
    assert response.status_code == 200
    assert response.json()["app_name"] == "WireGuard Mesh Manager"

    # Restore original value
    restore_data = {"app_name": current_data["app_name"]}
    await async_client.patch("/api/settings", json=restore_data)


@pytest.mark.asyncio
async def test_update_invalid_app_name(async_client: AsyncClient) -> None:
    """Test validation for invalid app name."""
    # Test empty string
    response = await async_client.patch(
        "/api/settings", json={"app_name": ""}
    )
    assert response.status_code == 422

    # Test string too long (101 characters)
    response = await async_client.patch(
        "/api/settings", json={"app_name": "X" * 101}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_invalid_logo_bg_color(async_client: AsyncClient) -> None:
    """Test validation for invalid logo background color."""
    # Test invalid hex format (missing #)
    response = await async_client.patch(
        "/api/settings", json={"logo_bg_color": "FF5733"}
    )
    assert response.status_code == 422

    # Test invalid hex format (too short)
    response = await async_client.patch(
        "/api/settings", json={"logo_bg_color": "#F5"}
    )
    assert response.status_code == 422

    # Test invalid hex format (5 characters)
    response = await async_client.patch(
        "/api/settings", json={"logo_bg_color": "#FF573"}
    )
    assert response.status_code == 422

    # Test invalid hex format (invalid characters)
    response = await async_client.patch(
        "/api/settings", json={"logo_bg_color": "#GG5733"}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_invalid_logo_text(async_client: AsyncClient) -> None:
    """Test validation for invalid logo text."""
    # Test text too long (4 characters)
    response = await async_client.patch(
        "/api/settings", json={"logo_text": "WXYZ"}
    )
    assert response.status_code == 422

    # Test non-alphanumeric characters
    response = await async_client.patch(
        "/api/settings", json={"logo_text": "W!"}
    )
    assert response.status_code == 422

    # Test text with spaces
    response = await async_client.patch(
        "/api/settings", json={"logo_text": "W G"}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_both_logo_settings(async_client: AsyncClient) -> None:
    """Test updating both logo settings together."""
    # Get current settings
    get_response = await async_client.get("/api/settings")
    assert get_response.status_code == 200
    current_data = get_response.json()

    # Update both settings
    update_data = {"logo_bg_color": "#12ABCD", "logo_text": "ABC"}
    response = await async_client.patch("/api/settings", json=update_data)
    assert response.status_code == 200

    # Verify updates
    updated_data = response.json()
    assert updated_data["logo_bg_color"] == "#12ABCD"
    assert updated_data["logo_text"] == "ABC"

    # Restore original values
    restore_data = {
        "logo_bg_color": current_data["logo_bg_color"],
        "logo_text": current_data["logo_text"],
    }
    await async_client.patch("/api/settings", json=restore_data)
