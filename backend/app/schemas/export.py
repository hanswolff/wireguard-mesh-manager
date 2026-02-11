"""Pydantic schemas for export/import operations."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ExportMetadata(BaseModel):
    """Metadata for export files."""

    version: str = Field(default="1.0")
    exported_at: datetime
    exported_by: str
    description: str | None = None


class LocationExport(BaseModel):
    """Location data for export."""

    name: Annotated[str, Field(min_length=1, max_length=100)]
    description: str | None = None
    external_endpoint: Annotated[str, Field(min_length=1, max_length=255)] | None = None
    internal_endpoint: Annotated[str, Field(min_length=1, max_length=255)] | None = None
    preshared_key_encrypted: Annotated[str | None, Field(min_length=1)] = None
    interface_properties: Annotated[
        dict[str, Any] | None, Field(description="Additional interface properties")
    ] = None


class DeviceExport(BaseModel):
    """Device data for export."""

    name: Annotated[str, Field(min_length=1, max_length=100)]
    description: str | None = None
    wireguard_ip: Annotated[str, Field(pattern=r"^\d+\.\d+\.\d+\.\d+$")]
    private_key_encrypted: str
    device_dek_encrypted_master: Annotated[str | None, Field(min_length=1)] = None
    device_dek_encrypted_api_key: Annotated[str | None, Field(min_length=1)] = None
    public_key: Annotated[str, Field(min_length=44, max_length=56)]
    preshared_key_encrypted: Annotated[str, Field(min_length=1)] | None = None
    network_preshared_key_encrypted: Annotated[str, Field(min_length=1)] | None = None
    location_preshared_key_encrypted: Annotated[str, Field(min_length=1)] | None = None
    enabled: bool = True
    location_name: Annotated[
        str, Field(min_length=1, max_length=100)
    ]  # Reference to location by name
    interface_properties: Annotated[
        dict[str, Any] | None, Field(description="Additional interface properties")
    ] = None


class WireGuardNetworkExport(BaseModel):
    """Complete network data for export.

    For mesh topology, networks do not have their own WireGuard keys.
    Key fields are optional to support both mesh (no keys) and legacy formats.
    """

    name: Annotated[str, Field(min_length=1, max_length=100)]
    description: str | None = None
    network_cidr: Annotated[str, Field(pattern=r"^\d+\.\d+\.\d+\.\d+/\d+$")]
    dns_servers: str | None = None
    mtu: Annotated[int, Field(gt=0, le=9000)] | None = None
    persistent_keepalive: Annotated[int, Field(ge=0, le=86400)] | None = None
    private_key_encrypted: Annotated[str | None, Field(min_length=1)] = None
    public_key: Annotated[str | None, Field(min_length=44, max_length=56)] = None
    preshared_key_encrypted: Annotated[str | None, Field(min_length=1)] = None
    interface_properties: Annotated[
        dict[str, Any] | None, Field(description="Additional interface properties")
    ] = None
    locations: list[LocationExport] = []
    devices: list[DeviceExport] = []


class ExportData(BaseModel):
    """Complete export data structure."""

    metadata: ExportMetadata
    networks: list[WireGuardNetworkExport] = []

    model_config = ConfigDict(
        ser_json_bytes_sort_keys=True,
        json_schema_extra={
            "example": {
                "metadata": {
                    "version": "1.0",
                    "exported_at": "2024-01-01T00:00:00Z",
                    "exported_by": "admin@example.com",
                    "description": "Backup of production networks",
                },
                "networks": [],
            }
        },
    )


class ExportRequest(BaseModel):
    """Request schema for exporting networks."""

    network_ids: list[str] | None = None
    include_configs: bool = True
    include_api_keys: bool = False
    format: Literal["json", "zip"] = "json"


class ExportConfigsRequest(BaseModel):
    """Request schema for exporting network device configurations."""

    format: Literal["wg", "json", "mobile"] = "wg"
    platform: str | None = None
    include_preshared_keys: bool = False
