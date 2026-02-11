"""Tests for WireGuard network API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient

    from app.database.models import WireGuardNetwork


pytestmark = pytest.mark.usefixtures("unlocked_master_password")


class TestNetworksAPI:
    """Test suite for network API endpoints."""

    async def test_list_networks_empty(self, async_client: AsyncClient) -> None:
        """Test listing networks when none exist."""
        response = await async_client.get("/api/networks/")
        assert response.status_code == 200
        assert response.json() == []

    async def test_create_network(self, async_client: AsyncClient) -> None:
        """Test creating a network."""
        network_data = {
            "name": "Test Network",
            "description": "A test network",
            "network_cidr": "10.0.0.0/24",
        }
        response = await async_client.post("/api/networks/", json=network_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == network_data["name"]
        assert data["description"] == network_data["description"]
        assert data["network_cidr"] == network_data["network_cidr"]
        assert data["location_count"] == 0
        assert data["device_count"] == 0
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    async def test_create_network_duplicate_name(
        self, async_client: AsyncClient
    ) -> None:
        """Test creating a network with duplicate name."""
        network_data = {
            "name": "Test Network",
            "description": "A test network",
            "network_cidr": "10.0.0.0/24",
        }
        # Create first network
        await async_client.post("/api/networks/", json=network_data)

        # Try to create second with same name
        response = await async_client.post("/api/networks/", json=network_data)
        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "validation_error"
        assert any(
            "already exists" in detail["msg"] for detail in data.get("details", [])
        )

    async def test_create_network_duplicate_cidr(
        self, async_client: AsyncClient
    ) -> None:
        """Test creating a network with duplicate CIDR."""
        # Create first network
        network_data_1 = {
            "name": "Test Network 1",
            "description": "A test network",
            "network_cidr": "10.0.0.0/24",
        }
        await async_client.post("/api/networks/", json=network_data_1)

        # Try to create second network with same CIDR but different name
        network_data_2 = {
            "name": "Test Network 2",
            "description": "Another test network",
            "network_cidr": "10.0.0.0/24",
        }
        response = await async_client.post("/api/networks/", json=network_data_2)
        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "validation_error"
        assert any(
            "already exists" in detail["msg"] for detail in data.get("details", [])
        )

    async def test_get_network(
        self, async_client: AsyncClient, sample_network: WireGuardNetwork
    ) -> None:
        """Test getting a specific network."""
        response = await async_client.get(f"/api/networks/{sample_network.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_network.id
        assert data["name"] == sample_network.name

    async def test_get_network_not_found(self, async_client: AsyncClient) -> None:
        """Test getting a non-existent network."""
        fake_id = "550e8400-e29b-41d4-a716-446655440000"
        response = await async_client.get(f"/api/networks/{fake_id}")
        assert response.status_code == 404
        assert "not found" in response.json()["message"]

    async def test_update_network(
        self, async_client: AsyncClient, sample_network: WireGuardNetwork
    ) -> None:
        """Test updating a network."""
        update_data = {
            "name": "Updated Network",
            "description": "Updated description",
        }
        response = await async_client.put(
            f"/api/networks/{sample_network.id}", json=update_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]

    async def test_update_network_duplicate_cidr(
        self, async_client: AsyncClient
    ) -> None:
        """Test updating a network to use a duplicate CIDR."""
        # Create first network
        network_data_1 = {
            "name": "Test Network 1",
            "description": "A test network",
            "network_cidr": "10.0.0.0/24",
        }
        await async_client.post("/api/networks/", json=network_data_1)

        # Create second network with different CIDR
        network_data_2 = {
            "name": "Test Network 2",
            "description": "Another test network",
            "network_cidr": "10.0.1.0/24",
        }
        create_response_2 = await async_client.post("/api/networks/", json=network_data_2)
        network_id_2 = create_response_2.json()["id"]

        # Try to update second network to use first network's CIDR
        update_data = {
            "network_cidr": "10.0.0.0/24",
        }
        response = await async_client.put(f"/api/networks/{network_id_2}", json=update_data)
        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "validation_error"
        assert any(
            "already exists" in detail["msg"] for detail in data.get("details", [])
        )

    async def test_update_network_not_found(self, async_client: AsyncClient) -> None:
        """Test updating a non-existent network."""
        fake_id = "550e8400-e29b-41d4-a716-446655440000"
        update_data = {"name": "Updated Network"}
        response = await async_client.put(f"/api/networks/{fake_id}", json=update_data)
        assert response.status_code == 404

    async def test_delete_network(self, async_client: AsyncClient) -> None:
        """Test deleting a network without locations."""
        # First create a network
        network_data = {
            "name": "Network to Delete",
            "description": "A network created for deletion testing",
            "network_cidr": "10.0.1.0/24",
        }
        create_response = await async_client.post("/api/networks/", json=network_data)
        assert create_response.status_code == 201
        network_id = create_response.json()["id"]

        # Now delete it
        response = await async_client.delete(f"/api/networks/{network_id}")
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]

        # Verify it's deleted
        get_response = await async_client.get(f"/api/networks/{network_id}")
        assert get_response.status_code == 404

    async def test_delete_network_not_found(self, async_client: AsyncClient) -> None:
        """Test deleting a non-existent network."""
        fake_id = "550e8400-e29b-41d4-a716-446655440000"
        response = await async_client.delete(f"/api/networks/{fake_id}")
        assert response.status_code == 404

    async def test_delete_network_with_locations(
        self,
        async_client: AsyncClient,
        sample_network: WireGuardNetwork,
        sample_location,
    ) -> None:
        """Test deleting a network that has locations."""
        response = await async_client.delete(f"/api/networks/{sample_network.id}")
        assert response.status_code == 409
        assert "has locations" in response.json()["message"]

    async def test_create_network_validation_error(
        self, async_client: AsyncClient
    ) -> None:
        """Test creating a network with invalid data."""
        invalid_data = {
            "name": "",  # Empty name should fail
            "network_cidr": "invalid-cidr",  # Invalid CIDR should fail
        }
        response = await async_client.post("/api/networks/", json=invalid_data)
        assert response.status_code == 422
        assert "validation_error" in response.json()["error"]
