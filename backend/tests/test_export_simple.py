"""Simple test for export functionality to verify it works."""

import json
from datetime import UTC, datetime

from app.schemas.export import ExportData, ExportMetadata, WireGuardNetworkExport


def test_export_schema_validation() -> None:
    """Test that the export schema works correctly."""
    # Create a basic export with network keys
    export_data = ExportData(
        metadata=ExportMetadata(
            version="1.0",
            exported_at=datetime.now(UTC),
            exported_by="test@example.com",
            description="Test export",
        ),
        networks=[
            WireGuardNetworkExport(
                name="Test Network",
                description="A test network",
                network_cidr="10.0.0.0/24",
                private_key_encrypted="encrypted_key",
                public_key="YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=",
                locations=[],
                devices=[],
            )
        ],
    )

    # Test serialization
    json_str = export_data.model_dump_json()
    assert json_str is not None

    # Test deserialization
    parsed_data = json.loads(json_str)
    restored_export = ExportData.model_validate(parsed_data)

    assert restored_export.metadata.exported_by == "test@example.com"
    assert len(restored_export.networks) == 1
    assert restored_export.networks[0].name == "Test Network"


def test_export_schema_mesh_topology() -> None:
    """Test that the export schema works with mesh topology (no network keys)."""
    # Create an export without network keys (mesh topology format)
    export_data = ExportData(
        metadata=ExportMetadata(
            version="1.0",
            exported_at=datetime.now(UTC),
            exported_by="test@example.com",
            description="Test mesh topology export",
        ),
        networks=[
            WireGuardNetworkExport(
                name="Mesh Network",
                description="A mesh topology network",
                network_cidr="10.0.0.0/24",
                private_key_encrypted=None,
                public_key=None,
                preshared_key_encrypted=None,
                locations=[],
                devices=[],
            )
        ],
    )

    # Test serialization
    json_str = export_data.model_dump_json()
    assert json_str is not None

    # Test deserialization
    parsed_data = json.loads(json_str)
    restored_export = ExportData.model_validate(parsed_data)

    assert restored_export.metadata.exported_by == "test@example.com"
    assert len(restored_export.networks) == 1
    assert restored_export.networks[0].name == "Mesh Network"
    assert restored_export.networks[0].private_key_encrypted is None
    assert restored_export.networks[0].public_key is None


def test_export_schema_backward_compatibility() -> None:
    """Test backward compatibility with old exports that have network keys."""
    old_export_json = """{
        "metadata": {
            "version": "1.0",
            "exported_at": "2024-01-01T00:00:00Z",
            "exported_by": "admin@example.com",
            "description": "Legacy export"
        },
        "networks": [
            {
                "name": "Old Network",
                "description": "A network from before mesh topology",
                "network_cidr": "192.168.1.0/24",
                "dns_servers": "1.1.1.1",
                "mtu": 1280,
                "persistent_keepalive": 25,
                "private_key_encrypted": "encrypted_key_value",
                "public_key": "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=",
                "preshared_key_encrypted": "encrypted_psk",
                "interface_properties": null,
                "locations": [],
                "devices": []
            }
        ]
    }"""

    parsed_data = json.loads(old_export_json)
    export = ExportData.model_validate(parsed_data)

    assert len(export.networks) == 1
    network = export.networks[0]
    assert network.name == "Old Network"
    assert network.private_key_encrypted == "encrypted_key_value"
    assert network.public_key == "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE="
    assert network.preshared_key_encrypted == "encrypted_psk"


def test_export_schema_json_compatibility() -> None:
    """Test JSON schema generation for the export format."""
    schema = ExportData.model_json_schema()

    assert "metadata" in schema["properties"]
    assert "networks" in schema["properties"]
    # Check that schema is a valid JSON schema
    assert "$defs" in schema  # Pydantic uses $defs for definitions
