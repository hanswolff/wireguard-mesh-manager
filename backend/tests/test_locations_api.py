"""Tests for location API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from httpx import AsyncClient

    from app.database.models import Location, WireGuardNetwork


class TestLocationsAPI:
    """Test suite for location API endpoints."""

    async def test_list_locations_empty(self, async_client: AsyncClient) -> None:
        """Test listing locations when none exist."""
        response = await async_client.get("/api/locations/")
        assert response.status_code == 200
        assert response.json() == []

    async def test_create_location(
        self, async_client: AsyncClient, sample_network: WireGuardNetwork
    ) -> None:
        """Test creating a location."""
        location_data = {
            "network_id": sample_network.id,
            "name": "Test Location",
            "description": "A test location",
            "external_endpoint": "192.168.1.100",
        }
        response = await async_client.post("/api/locations/", json=location_data)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == location_data["name"]
        assert data["description"] == location_data["description"]
        assert data["external_endpoint"] == location_data["external_endpoint"]
        assert data["network_id"] == location_data["network_id"]
        assert data["device_count"] == 0
        assert "id" in data
        assert "created_at" in data

    async def test_create_location_invalid_network(
        self, async_client: AsyncClient
    ) -> None:
        """Test creating a location with invalid network ID."""
        fake_network_id = "550e8400-e29b-41d4-a716-446655440000"
        location_data = {
            "network_id": fake_network_id,
            "name": "Test Location",
            "description": "A test location",
        }
        response = await async_client.post("/api/locations/", json=location_data)
        assert response.status_code == 404
        assert "not found" in response.json()["message"]

    async def test_create_location_duplicate_name(
        self,
        async_client: AsyncClient,
        sample_network: WireGuardNetwork,
        sample_location: Location,
    ) -> None:
        """Test creating a location with duplicate name in same network."""
        location_data = {
            "network_id": sample_network.id,
            "name": sample_location.name,  # Same name in same network
            "description": "Another location",
        }
        response = await async_client.post("/api/locations/", json=location_data)
        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "validation_error"
        assert any(
            "already exists" in detail["msg"] for detail in data.get("details", [])
        )

    async def test_get_location(
        self, async_client: AsyncClient, sample_location: Location
    ) -> None:
        """Test getting a specific location."""
        response = await async_client.get(f"/api/locations/{sample_location.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_location.id
        assert data["name"] == sample_location.name

    async def test_get_location_not_found(self, async_client: AsyncClient) -> None:
        """Test getting a non-existent location."""
        fake_id = "550e8400-e29b-41d4-a716-446655440000"
        response = await async_client.get(f"/api/locations/{fake_id}")
        assert response.status_code == 404
        assert "not found" in response.json()["message"]

    async def test_update_location(
        self, async_client: AsyncClient, sample_location: Location
    ) -> None:
        """Test updating a location."""
        update_data = {
            "name": "Updated Location",
            "description": "Updated description",
        }
        response = await async_client.put(
            f"/api/locations/{sample_location.id}", json=update_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]

    async def test_update_location_not_found(self, async_client: AsyncClient) -> None:
        """Test updating a non-existent location."""
        fake_id = "550e8400-e29b-41d4-a716-446655440000"
        update_data = {"name": "Updated Location"}
        response = await async_client.put(f"/api/locations/{fake_id}", json=update_data)
        assert response.status_code == 404

    async def test_delete_location(
        self, async_client: AsyncClient, sample_location: Location
    ) -> None:
        """Test deleting a location."""
        # Create a second location first to avoid violating the "at least one location" rule
        response = await async_client.post(
            "/api/locations/",
            json={
                "network_id": sample_location.network_id,
                "name": "Another Location",
                "description": "Another test location",
            },
        )
        assert response.status_code == 201

        # Now delete the original location
        response = await async_client.delete(f"/api/locations/{sample_location.id}")
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]

        # Verify it's deleted
        get_response = await async_client.get(f"/api/locations/{sample_location.id}")
        assert get_response.status_code == 404

    async def test_delete_last_location_in_network(
        self, async_client: AsyncClient, sample_location: Location
    ) -> None:
        """Test deleting the last location in a network."""
        response = await async_client.delete(f"/api/locations/{sample_location.id}")
        assert response.status_code == 409
        assert "last location" in response.json()["message"]

    async def test_delete_location_with_devices(
        self, async_client: AsyncClient, sample_location: Location, sample_device
    ) -> None:
        """Test deleting a location that has devices."""
        response = await async_client.delete(f"/api/locations/{sample_location.id}")
        assert response.status_code == 409
        assert "has devices" in response.json()["message"]

    async def test_create_location_validation_error(
        self, async_client: AsyncClient
    ) -> None:
        """Test creating a location with invalid data."""
        invalid_data = {
            "network_id": "",  # Empty network ID should fail
            "name": "",  # Empty name should fail
        }
        response = await async_client.post("/api/locations/", json=invalid_data)
        assert response.status_code == 422
        assert "validation_error" in response.json()["error"]

    async def test_list_locations_by_network_id(
        self,
        async_client: AsyncClient,
        sample_network: WireGuardNetwork,
    ) -> None:
        """Test listing locations filtered by network ID."""
        # Create a second network
        network_response_2 = await async_client.post(
            "/api/networks/",
            json={
                "name": "Second Network",
                "description": "A second network",
                "network_cidr": "10.0.1.0/24",
            },
        )
        assert network_response_2.status_code == 201
        network_id_2 = network_response_2.json()["id"]

        # Create a location in the first network
        location_response_1 = await async_client.post(
            "/api/locations/",
            json={
                "network_id": sample_network.id,
                "name": "Location in Network 1",
                "description": "First network location",
            },
        )
        assert location_response_1.status_code == 201
        location_id_1 = location_response_1.json()["id"]

        # Create a location in the second network
        location_response_2 = await async_client.post(
            "/api/locations/",
            json={
                "network_id": network_id_2,
                "name": "Location in Network 2",
                "description": "Second network location",
            },
        )
        assert location_response_2.status_code == 201
        location_id_2 = location_response_2.json()["id"]

        # List all locations (should return both)
        all_response = await async_client.get("/api/locations/")
        assert all_response.status_code == 200
        all_locations = all_response.json()
        assert len(all_locations) == 2

        # List locations filtered by first network ID
        network_1_response = await async_client.get(
            f"/api/locations/?network_id={sample_network.id}"
        )
        assert network_1_response.status_code == 200
        network_1_locations = network_1_response.json()
        assert len(network_1_locations) == 1
        assert network_1_locations[0]["id"] == location_id_1
        assert network_1_locations[0]["network_id"] == sample_network.id

        # List locations filtered by second network ID
        network_2_response = await async_client.get(
            f"/api/locations/?network_id={network_id_2}"
        )
        assert network_2_response.status_code == 200
        network_2_locations = network_2_response.json()
        assert len(network_2_locations) == 1
        assert network_2_locations[0]["id"] == location_id_2
        assert network_2_locations[0]["network_id"] == network_id_2

        # Filter by invalid network ID
        invalid_response = await async_client.get(
            "/api/locations/?network_id=invalid-uuid"
        )
        assert invalid_response.status_code == 200
        assert invalid_response.json() == []

    async def test_create_location_with_empty_external_endpoint(
        self, async_client: AsyncClient, sample_network: WireGuardNetwork
    ) -> None:
        """Test creating a location with empty external endpoint."""
        location_data = {
            "network_id": sample_network.id,
            "name": "Test Location",
            "description": "A test location",
            "external_endpoint": "",
        }
        response = await async_client.post("/api/locations/", json=location_data)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == location_data["name"]
        assert data["description"] == location_data["description"]
        assert data["external_endpoint"] is None  # Empty string should become None
        assert data["network_id"] == location_data["network_id"]

    async def test_create_location_with_none_external_endpoint(
        self, async_client: AsyncClient, sample_network: WireGuardNetwork
    ) -> None:
        """Test creating a location with None external endpoint."""
        location_data = {
            "network_id": sample_network.id,
            "name": "Test Location",
            "description": "A test location",
            "external_endpoint": None,
        }
        response = await async_client.post("/api/locations/", json=location_data)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == location_data["name"]
        assert data["description"] == location_data["description"]
        assert data["external_endpoint"] is None
        assert data["network_id"] == location_data["network_id"]

    async def test_update_location_with_empty_external_endpoint(
        self, async_client: AsyncClient, sample_location: Location
    ) -> None:
        """Test updating a location with empty external endpoint."""
        update_data = {
            "external_endpoint": "",
        }
        response = await async_client.put(
            f"/api/locations/{sample_location.id}", json=update_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["external_endpoint"] is None  # Empty string should become None
