"""Tests for export/import API endpoints."""

from __future__ import annotations

import json
from io import BytesIO
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient

    from app.database.models import Device, Location, WireGuardNetwork


pytestmark = pytest.mark.usefixtures("unlocked_master_password")


class TestExportAPI:
    """Test suite for export/import API endpoints."""

    async def test_export_networks_empty(self, async_client: AsyncClient) -> None:
        """Test exporting networks when none exist."""
        response = await async_client.get("/api/export/networks")
        assert response.status_code == 200
        data = response.json()
        assert "metadata" in data
        assert data["metadata"]["version"] == "1.0"
        assert data["networks"] == []

    async def test_export_networks_with_data(
        self,
        async_client: AsyncClient,
        test_network: WireGuardNetwork,
        test_location: Location,
        test_device: Device,
    ) -> None:
        """Test exporting networks with data."""
        response = await async_client.get(
            "/api/export/networks?exported_by=test@example.com&description=Test export"
        )
        assert response.status_code == 200
        data = response.json()

        # Check metadata
        assert data["metadata"]["exported_by"] == "test@example.com"
        assert data["metadata"]["description"] == "Test export"
        assert data["metadata"]["version"] == "1.0"
        assert "exported_at" in data["metadata"]

        # Check network data
        assert len(data["networks"]) == 1
        network = data["networks"][0]
        assert network["name"] == test_network.name
        assert network["description"] == test_network.description
        assert network["network_cidr"] == test_network.network_cidr

        # Check locations
        assert len(network["locations"]) == 1
        location = network["locations"][0]
        assert location["name"] == test_location.name
        assert location["description"] == test_location.description
        assert location["external_endpoint"] == test_location.external_endpoint

        # Check devices
        assert len(network["devices"]) == 1
        device = network["devices"][0]
        assert device["name"] == test_device.name
        assert device["description"] == test_device.description
        assert device["wireguard_ip"] == test_device.wireguard_ip
        assert device["public_key"] == test_device.public_key
        assert device["location_name"] == test_location.name

    async def test_import_networks_new(self, async_client: AsyncClient) -> None:
        """Test importing new networks."""
        # Create export data
        export_data = {
            "metadata": {
                "version": "1.0",
                "exported_at": "2024-01-01T00:00:00Z",
                "exported_by": "test@example.com",
                "description": "Test export",
            },
            "networks": [
                {
                    "name": "Imported Network",
                    "description": "A network for testing import",
                    "network_cidr": "192.168.100.0/24",
                    "dns_servers": "8.8.8.8,8.8.4.4",
                    "mtu": 1420,
                    "persistent_keepalive": 25,
                    "private_key_encrypted": "encrypted_server_key",
                    "public_key": "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=",
                    "locations": [
                        {
                            "name": "Office",
                            "description": "Main office location",
                            "external_endpoint": "office.example.com:51821",
                        }
                    ],
                    "devices": [
                        {
                            "name": "laptop-john",
                            "description": "John's work laptop",
                            "wireguard_ip": "192.168.100.10",
                            "private_key_encrypted": "encrypted_device_key",
                            "public_key": "TRqhSNRCsowwmwouBgrz4WEuVJ2q3h1N2MHdNnLVzH0=",
                            "preshared_key_encrypted": None,
                            "enabled": True,
                            "location_name": "Office",
                        }
                    ],
                }
            ],
        }

        # Create file-like object
        file_content = BytesIO(json.dumps(export_data).encode("utf-8"))
        file_content.name = "export.json"

        # Upload and import
        files = {"file": ("export.json", file_content, "application/json")}
        response = await async_client.post(
            "/api/export/networks?imported_by=test@example.com&overwrite_existing=false",
            files=files,
        )

        assert response.status_code == 200
        results = response.json()
        assert results["networks_created"] == 1
        assert results["networks_updated"] == 0
        assert results["locations_created"] == 1
        assert results["devices_created"] == 1
        assert results["errors"] == []

        # Verify the data was imported correctly
        response = await async_client.get("/api/networks/")
        assert response.status_code == 200
        networks = response.json()
        assert len(networks) == 1
        assert networks[0]["name"] == "Imported Network"

    async def test_import_networks_duplicate_name(
        self, async_client: AsyncClient, test_network: WireGuardNetwork
    ) -> None:
        """Test importing networks with duplicate names without overwrite."""
        export_data = {
            "metadata": {
                "version": "1.0",
                "exported_at": "2024-01-01T00:00:00Z",
                "exported_by": "test@example.com",
            },
            "networks": [
                {
                    "name": test_network.name,
                    "description": "Duplicate network",
                    "network_cidr": "192.168.100.0/24",
                    "private_key_encrypted": "encrypted_key",
                    "public_key": "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=",
                    "locations": [],
                    "devices": [],
                }
            ],
        }

        file_content = BytesIO(json.dumps(export_data).encode("utf-8"))
        files = {"file": ("export.json", file_content, "application/json")}
        response = await async_client.post(
            "/api/export/networks?overwrite_existing=false", files=files
        )

        assert response.status_code == 409  # Conflict
        results = response.json()
        assert results["networks_created"] == 0
        assert results["networks_updated"] == 0
        assert len(results["errors"]) > 0
        assert "already exists" in results["errors"][0]

    async def test_import_networks_overwrite(
        self, async_client: AsyncClient, sample_network: WireGuardNetwork
    ) -> None:
        """Test importing networks with overwrite enabled."""
        export_data = {
            "metadata": {
                "version": "1.0",
                "exported_at": "2024-01-01T00:00:00Z",
                "exported_by": "test@example.com",
            },
            "networks": [
                {
                    "name": sample_network.name,
                    "description": "Updated description",
                    "network_cidr": sample_network.network_cidr,
                    "private_key_encrypted": sample_network.private_key_encrypted,
                    "public_key": sample_network.public_key,
                    "locations": [],
                    "devices": [],
                }
            ],
        }

        file_content = BytesIO(json.dumps(export_data).encode("utf-8"))
        files = {"file": ("export.json", file_content, "application/json")}
        response = await async_client.post(
            "/api/export/networks?overwrite_existing=true", files=files
        )

        assert response.status_code == 200
        results = response.json()
        assert results["networks_created"] == 0
        assert results["networks_updated"] == 1
        assert results["errors"] == []

    async def test_import_invalid_json(self, async_client: AsyncClient) -> None:
        """Test importing invalid JSON."""
        file_content = BytesIO(b"invalid json content")
        files = {"file": ("export.json", file_content, "application/json")}
        response = await async_client.post("/api/export/networks", files=files)

        assert response.status_code == 400
        assert "Invalid JSON file" in response.json()["detail"]

    async def test_import_non_json_file(self, async_client: AsyncClient) -> None:
        """Test importing non-JSON file."""
        file_content = BytesIO(b"some text content")
        files = {"file": ("export.txt", file_content, "text/plain")}
        response = await async_client.post("/api/export/networks", files=files)

        assert response.status_code == 400
        assert "Only JSON files are supported" in response.json()["detail"]

    async def test_import_invalid_schema(self, async_client: AsyncClient) -> None:
        """Test importing JSON with invalid schema."""
        invalid_data = {
            "metadata": {
                "version": "2.0",  # Unsupported version
                "exported_at": "2024-01-01T00:00:00Z",
                "exported_by": "test@example.com",
            },
            "networks": [],
        }

        file_content = BytesIO(json.dumps(invalid_data).encode("utf-8"))
        files = {"file": ("export.json", file_content, "application/json")}
        response = await async_client.post("/api/export/networks", files=files)

        assert response.status_code == 422
        results = response.json()
        assert len(results["errors"]) > 0
        assert "unsupported export version" in results["errors"][0].lower()

    async def test_get_export_schema(self, async_client: AsyncClient) -> None:
        """Test getting export schema."""
        response = await async_client.get("/api/export/networks/schema")
        assert response.status_code == 200
        schema = response.json()
        assert "$schema" in schema
        assert "type" in schema
        assert "properties" in schema
        assert "metadata" in schema["properties"]
        assert "networks" in schema["properties"]

    async def test_import_device_unknown_location(
        self, async_client: AsyncClient
    ) -> None:
        """Test importing device that references unknown location."""
        export_data = {
            "metadata": {
                "version": "1.0",
                "exported_at": "2024-01-01T00:00:00Z",
                "exported_by": "test@example.com",
            },
            "networks": [
                {
                    "name": "Test Network",
                    "network_cidr": "192.168.100.0/24",
                    "private_key_encrypted": "encrypted_key",
                    "public_key": "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=",
                    "locations": [
                        {
                            "name": "Office",
                            "description": "Office location",
                            "external_endpoint": None,
                        }
                    ],
                    "devices": [
                        {
                            "name": "test-device",
                            "wireguard_ip": "192.168.100.10",
                            "private_key_encrypted": "encrypted_device_key",
                            "public_key": "TRqhSNRCsowwmwouBgrz4WEuVJ2q3h1N2MHdNnLVzH0=",
                            "enabled": True,
                            "location_name": "UnknownLocation",  # This location doesn't exist
                        }
                    ],
                }
            ],
        }

        file_content = BytesIO(json.dumps(export_data).encode("utf-8"))
        files = {"file": ("export.json", file_content, "application/json")}
        response = await async_client.post("/api/export/networks", files=files)

        assert response.status_code == 200
        results = response.json()
        assert results["networks_created"] == 1
        assert results["locations_created"] == 1
        assert results["devices_created"] == 0
        assert len(results["errors"]) > 0
        assert "unknown location" in results["errors"][0]
