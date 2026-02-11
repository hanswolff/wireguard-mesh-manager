"""Pydantic schemas for device configuration retrieval."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, Field, field_validator


class WireGuardInterfaceConfig(BaseModel):
    """WireGuard interface configuration."""

    private_key: Annotated[str, Field(description="Device's private key")]
    address: Annotated[
        str, Field(description="Device's WireGuard IP address with CIDR")
    ]
    dns: Annotated[str | None, Field(description="DNS servers for the device")] = None
    mtu: Annotated[
        int | None, Field(ge=576, le=9000, description="MTU for the device")
    ] = None
    listen_port: Annotated[
        int | None, Field(ge=1, le=65535, description="ListenPort for the device")
    ] = None
    interface_properties: Annotated[
        dict[str, Any] | None,
        Field(description="Additional interface properties as key-value pairs"),
    ] = None


class WireGuardPeerConfig(BaseModel):
    """WireGuard peer configuration (device-to-device connection for mesh topology)."""

    name: Annotated[str | None, Field(description="Peer device name")] = None
    public_key: Annotated[str, Field(description="Peer's public key")]
    allowed_ips: Annotated[str, Field(description="Allowed IPs for this peer")]
    endpoint: Annotated[str | None, Field(description="Peer endpoint (host:port)")] = (
        None
    )
    persistent_keepalive: Annotated[
        int | None, Field(ge=0, le=86400, description="Persistent keepalive interval")
    ] = None
    preshared_key: Annotated[
        str | None, Field(description="Optional preshared key")
    ] = None
    peer_properties: Annotated[
        dict[str, Any] | None,
        Field(description="Additional peer properties as key-value pairs"),
    ] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Peer Device 1",
                "public_key": "def456...",
                "allowed_ips": "10.0.0.3/32",
                "endpoint": "device3.example.com:51820",
                "persistent_keepalive": 25,
                "preshared_key": None,
                "peer_properties": {"PersistentKeepalive": 25},
            }
        }
    }


class DeviceConfiguration(BaseModel):
    """Complete device configuration for mesh topology.

    Contains interface configuration and a list of peer configurations
    representing all other devices in the network.
    """

    interface: WireGuardInterfaceConfig
    peers: Annotated[
        list[WireGuardPeerConfig],
        Field(description="List of peer configurations for mesh topology"),
    ]

    model_config = {
        "ser_json_bytes_sort_keys": True,
        "json_schema_extra": {
            "example": {
                "interface": {
                    "private_key": "abc123...",
                    "address": "10.0.0.2/24",
                    "dns": "8.8.8.8,8.8.4.4",
                },
                "peers": [
                    {
                        "public_key": "def456...",
                        "allowed_ips": "10.0.0.3/32",
                        "endpoint": "device3.example.com:51820",
                        "persistent_keepalive": 25,
                    },
                    {
                        "public_key": "ghi789...",
                        "allowed_ips": "10.0.0.4/32",
                        "endpoint": "192.168.1.10:51820",
                        "persistent_keepalive": 25,
                    },
                ],
            }
        },
    }


class DeviceConfigRequest(BaseModel):
    """Request for device configuration."""

    format: Annotated[
        str, Field(default="wg", description="Configuration format: 'wg', 'json'")
    ]
    platform: Annotated[
        str | None,
        Field(description="Mobile platform for optimized config: 'ios', 'android'"),
    ] = None

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        """Validate the format parameter."""
        allowed_formats = {"wg", "json", "ini"}
        if v not in allowed_formats:
            raise ValueError(f"Format must be one of: {', '.join(allowed_formats)}")
        return v

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: str | None) -> str | None:
        """Validate the platform parameter."""
        if v is None:
            return v
        allowed_platforms = {"ios", "android", "windows", "macos", "linux"}
        if v not in allowed_platforms:
            raise ValueError(f"Platform must be one of: {', '.join(allowed_platforms)}")
        return v


class MobileConfig(BaseModel):
    """Mobile-specific configuration."""

    name: Annotated[str, Field(description="Configuration name for mobile app")]
    addresses: Annotated[list[str], Field(description="IP addresses")]
    dns: Annotated[list[str], Field(description="DNS servers")]
    mtu: Annotated[int | None, Field(ge=576, le=9000)] = None

    # Peer information
    public_key: Annotated[str, Field(description="Peer public key")]
    allowed_ips: Annotated[list[str], Field(description="Allowed IP ranges")]
    endpoint: Annotated[str | None, Field(description="Server endpoint")] = None
    persistent_keepalive: Annotated[int | None, Field(ge=0, le=86400)] = None

    model_config = {"ser_json_bytes_sort_keys": True}


class DeviceConfigResponse(BaseModel):
    """Device configuration response."""

    device_id: str
    device_name: str
    network_name: str
    configuration: str | DeviceConfiguration | MobileConfig
    format: str
    created_at: str

    model_config = {
        "ser_json_bytes_sort_keys": True,
        "json_schema_extra": {
            "example": {
                "device_id": "123e4567-e89b-12d3-a456-426614174000",
                "device_name": "iPhone 15",
                "network_name": "Company VPN",
                "configuration": "[Interface]\nPrivateKey = ...\nAddress = 10.0.0.2/24\n\n[Peer]\nPublicKey = ...\nAllowedIPs = 0.0.0.0/0\nEndpoint = vpn.example.com:51820",
                "format": "wg",
                "created_at": "2024-01-01T12:00:00Z",
            }
        },
    }
