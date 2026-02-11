"""Tests for WireGuard key generation API endpoint."""

from __future__ import annotations

import pytest

from app.main import app
from tests.conftest import AsyncSessionContext, get_test_client

pytestmark = pytest.mark.usefixtures("unlocked_master_password")


@pytest.mark.asyncio
async def test_generate_keys_cli_method(mock_session) -> None:
    """Test generating WireGuard keys using CLI method."""
    client = get_test_client(app, mock_session, authenticated=True)

    response = client.post(
        "/api/devices/generate-keys",
        json={"method": "cli"},
    )

    # Response should be successful (either CLI or crypto method)
    assert response.status_code == 200
    data = response.json()

    # Response should contain both keys
    assert "private_key" in data
    assert "public_key" in data
    assert "method" in data

    # Keys should be valid base64 (44 chars for 32 bytes)
    assert len(data["private_key"]) == 44
    assert len(data["public_key"]) == 44

    # Keys should be different
    assert data["private_key"] != data["public_key"]


@pytest.mark.asyncio
async def test_generate_keys_crypto_method(mock_session) -> None:
    """Test generating WireGuard keys using crypto method."""
    client = get_test_client(app, mock_session, authenticated=True)

    response = client.post(
        "/api/devices/generate-keys",
        json={"method": "crypto"},
    )

    assert response.status_code == 200
    data = response.json()

    assert "private_key" in data
    assert "public_key" in data
    assert data["method"] == "crypto"

    # Keys should be valid base64
    assert len(data["private_key"]) == 44
    assert len(data["public_key"]) == 44


@pytest.mark.asyncio
async def test_generate_keys_cli_fallback_to_crypto(mock_session, monkeypatch) -> None:
    """Test CLI method falls back to crypto when CLI tools are not available."""
    client = get_test_client(app, mock_session, authenticated=True)

    # Monkey-patch to simulate CLI failure
    from app.utils import key_management

    original_cli_func = key_management.generate_wireguard_keypair_cli

    def mock_cli_failure():
        raise RuntimeError("WireGuard CLI tools are not installed")

    monkeypatch.setattr(
        key_management, "generate_wireguard_keypair_cli", mock_cli_failure
    )

    try:
        response = client.post(
            "/api/devices/generate-keys",
            json={"method": "cli"},
        )

        # Should fall back to crypto method successfully
        assert response.status_code == 200
        data = response.json()

        assert "private_key" in data
        assert "public_key" in data
        assert data["method"] == "crypto"  # Should indicate fallback method
    finally:
        # Restore original function
        monkeypatch.setattr(
            key_management,
            "generate_wireguard_keypair_cli",
            original_cli_func,
        )


@pytest.mark.asyncio
async def test_generate_keys_unique_on_multiple_calls(mock_session) -> None:
    """Test that each key generation produces unique keys."""
    client = get_test_client(app, mock_session, authenticated=True)

    # Generate first pair
    response1 = client.post(
        "/api/devices/generate-keys",
        json={"method": "crypto"},
    )
    data1 = response1.json()
    keys1 = (data1["private_key"], data1["public_key"])

    # Generate second pair
    response2 = client.post(
        "/api/devices/generate-keys",
        json={"method": "crypto"},
    )
    data2 = response2.json()
    keys2 = (data2["private_key"], data2["public_key"])

    # All keys should be different
    assert keys1 != keys2
    assert data1["private_key"] != data2["private_key"]
    assert data1["public_key"] != data2["public_key"]


@pytest.mark.asyncio
async def test_generate_keys_unauthenticated(mock_session) -> None:
    """Test that key generation requires authentication."""
    client = get_test_client(app, mock_session, authenticated=False)

    response = client.post(
        "/api/devices/generate-keys",
        json={"method": "crypto"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_regenerate_device_keys(
    test_network, test_location, mock_session, unlocked_master_password
) -> None:
    """Test regenerating keys for an existing device."""
    client = get_test_client(app, mock_session, authenticated=True)

    # Create a device first
    device_data = {
        "network_id": test_network.id,
        "location_id": test_location.id,
        "name": "test-device-key-regeneration",
        "public_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
        "internal_endpoint_host": "192.168.1.100",
        "internal_endpoint_port": 51820,
    }

    async with AsyncSessionContext(mock_session):
        create_response = client.post("/api/devices/", json=device_data)
        device_id = create_response.json()["id"]
        original_public_key = create_response.json()["public_key"]

    # Regenerate keys
    regenerate_response = client.post(
        f"/api/devices/{device_id}/regenerate-keys",
        json={"method": "crypto"},
    )

    assert regenerate_response.status_code == 200
    data = regenerate_response.json()

    assert data["id"] == device_id
    assert data["public_key"] != original_public_key
    assert data["private_key_encrypted"] is True


@pytest.mark.asyncio
async def test_regenerate_device_keys_cli_fallback(
    test_network,
    test_location,
    mock_session,
    unlocked_master_password,
    monkeypatch,
) -> None:
    """Test device key regeneration with CLI fallback to crypto."""
    client = get_test_client(app, mock_session, authenticated=True)

    # Create a device first
    device_data = {
        "network_id": test_network.id,
        "location_id": test_location.id,
        "name": "test-device-cli-fallback",
        "public_key": "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB=",
        "internal_endpoint_host": "192.168.1.101",
        "internal_endpoint_port": 51821,
    }

    async with AsyncSessionContext(mock_session):
        create_response = client.post("/api/devices/", json=device_data)
        device_id = create_response.json()["id"]
        original_public_key = create_response.json()["public_key"]

    # Mock CLI failure
    from app.utils import key_management

    original_cli_func = key_management.generate_wireguard_keypair_cli

    def mock_cli_failure():
        raise RuntimeError("WireGuard CLI tools are not installed")

    monkeypatch.setattr(
        key_management, "generate_wireguard_keypair_cli", mock_cli_failure
    )

    try:
        # Regenerate keys - should fall back to crypto
        regenerate_response = client.post(
            f"/api/devices/{device_id}/regenerate-keys",
            json={"method": "cli"},
        )

        assert regenerate_response.status_code == 200
        data = regenerate_response.json()

        assert data["id"] == device_id
        assert data["public_key"] != original_public_key
        assert data["private_key_encrypted"] is True
    finally:
        # Restore original function
        monkeypatch.setattr(
            key_management,
            "generate_wireguard_keypair_cli",
            original_cli_func,
        )


@pytest.mark.asyncio
async def test_regenerate_device_keys_unauthorized(
    test_network, test_location, mock_session
) -> None:
    """Test that key regeneration requires unlocked master password."""
    client = get_test_client(app, mock_session, authenticated=True)

    # Create a device first
    device_data = {
        "network_id": test_network.id,
        "location_id": test_location.id,
        "name": "test-device-unauthorized",
        "public_key": "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC=",
        "internal_endpoint_host": "192.168.1.102",
        "internal_endpoint_port": 51822,
    }

    async with AsyncSessionContext(mock_session):
        create_response = client.post("/api/devices/", json=device_data)
        device_id = create_response.json()["id"]

    # Lock master password (remove it from cache)
    from app.utils.master_password import get_master_password_cache

    cache = get_master_password_cache()
    cache.clear()

    # Try to regenerate keys without unlocked master password
    regenerate_response = client.post(
        f"/api/devices/{device_id}/regenerate-keys",
        json={"method": "crypto"},
    )

    assert regenerate_response.status_code == 423
    assert "Master password must be unlocked" in regenerate_response.json()["detail"]


@pytest.mark.asyncio
async def test_regenerate_device_keys_nonexistent(mock_session) -> None:
    """Test regenerating keys for a non-existent device."""
    client = get_test_client(app, mock_session, authenticated=True)

    response = client.post(
        "/api/devices/nonexistent-id/regenerate-keys",
        json={"method": "crypto"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generate_keys_valid_base64(mock_session) -> None:
    """Test that generated keys are valid base64."""
    import base64

    client = get_test_client(app, mock_session, authenticated=True)

    response = client.post(
        "/api/devices/generate-keys",
        json={"method": "crypto"},
    )

    assert response.status_code == 200
    data = response.json()

    # Should decode as valid base64 without errors
    private_bytes = base64.b64decode(data["private_key"])
    public_bytes = base64.b64decode(data["public_key"])

    # Should be exactly 32 bytes (256 bits) for WireGuard keys
    assert len(private_bytes) == 32
    assert len(public_bytes) == 32
