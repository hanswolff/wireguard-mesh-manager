"""Pydantic schemas for WireGuard network operations."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import TYPE_CHECKING, Annotated, Any, TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.utils.key_management import validate_wireguard_key_import
from app.utils.validation import (
    ValidationError,
    validate_dns_servers,
    validate_interface_properties,
    validate_mtu,
    validate_network_cidr,
    validate_persistent_keepalive,
    validate_wireguard_public_key,
)

T = TypeVar("T")


def _validate_public_key_format(v: str | None) -> str | None:
    """Validate WireGuard public key format."""
    if v is None:
        return v
    try:
        validate_wireguard_public_key(v)
        return v
    except Exception as e:
        raise ValueError(str(e)) from e


def _validate_field(
    v: T | None,
    validator_func: Callable[[T], None],
    field_name: str,
) -> T | None:
    """Reusable field validator for optional fields.

    Args:
        v: Field value to validate
        validator_func: Validation function to call
        field_name: Name of the field for error messages

    Returns:
        Validated value or None

    Raises:
        ValueError: If validation fails
    """
    if v is None:
        return v
    try:
        validator_func(v)
        return v
    except Exception as e:
        raise ValueError(str(e)) from e


def _validate_preshared_key_format(v: str | None) -> str | None:
    """Validate WireGuard preshared key format."""
    if v is None:
        return v
    if isinstance(v, str) and v.strip() == "":
        return None
    try:
        return validate_wireguard_key_import(v, "preshared key")
    except Exception as e:
        raise ValueError(str(e)) from e


class WireGuardNetworkBase(BaseModel):
    """Base schema for WireGuard network."""

    name: Annotated[str, Field(min_length=1, max_length=100)]
    description: str | None = None
    network_cidr: Annotated[
        str, Field(description="Network CIDR notation (e.g., 10.0.0.0/24)")
    ]
    dns_servers: Annotated[
        str | None, Field(description="Comma-separated DNS servers (IP or domain)")
    ] = None
    mtu: Annotated[
        int | None, Field(description="Maximum transmission unit (576-9000 bytes)")
    ] = None
    persistent_keepalive: Annotated[
        int | None,
        Field(description="Persistent keepalive interval in seconds (0-86400)"),
    ] = None
    interface_properties: Annotated[
        dict[str, Any] | None,
        Field(
            description="Additional WireGuard interface properties as key-value pairs"
        ),
    ] = None

    @field_validator("interface_properties")
    @classmethod
    def validate_interface_properties_format(
        cls, v: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        """Validate interface properties format."""
        try:
            validate_interface_properties(v)
            return v
        except ValidationError as e:
            raise ValueError(str(e)) from e

    @field_validator("network_cidr")
    @classmethod
    def validate_network_cidr_format(cls, v: str) -> str:
        """Validate network CIDR format and practical constraints."""
        try:
            validate_network_cidr(v)
            return v
        except Exception as e:
            raise ValueError(str(e)) from e

    @field_validator("dns_servers")
    @classmethod
    def validate_dns_servers_format(cls, v: str | None) -> str | None:
        """Validate DNS servers format."""
        return _validate_field(v, validate_dns_servers, "dns_servers")

    @field_validator("mtu")
    @classmethod
    def validate_mtu_format(cls, v: int | None) -> int | None:
        """Validate MTU value."""
        return _validate_field(v, validate_mtu, "mtu")

    @field_validator("persistent_keepalive")
    @classmethod
    def validate_keepalive_format(cls, v: int | None) -> int | None:
        """Validate persistent keepalive value."""
        return _validate_field(v, validate_persistent_keepalive, "persistent_keepalive")


class WireGuardNetworkCreate(WireGuardNetworkBase):
    """Schema for creating a WireGuard network."""

    preshared_key: Annotated[
        str | None, Field(description="Optional preshared key")
    ] = None

    @field_validator("preshared_key")
    @classmethod
    def validate_preshared_key_format(cls, v: str | None) -> str | None:
        """Validate preshared key format."""
        return _validate_preshared_key_format(v)


class WireGuardNetworkUpdate(BaseModel):
    """Schema for updating a WireGuard network."""

    name: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    description: str | None = None
    network_cidr: (
        Annotated[str, Field(description="Network CIDR notation (e.g., 10.0.0.0/24)")]
        | None
    ) = None
    dns_servers: (
        Annotated[str, Field(description="Comma-separated DNS servers (IP or domain)")]
        | None
    ) = None
    mtu: (
        Annotated[int, Field(description="Maximum transmission unit (576-9000 bytes)")]
        | None
    ) = None
    persistent_keepalive: (
        Annotated[
            int, Field(description="Persistent keepalive interval in seconds (0-86400)")
        ]
        | None
    ) = None
    interface_properties: (
        Annotated[
            dict[str, Any],
            Field(
                description="Additional WireGuard interface properties as key-value pairs"
            ),
        ]
        | None
    ) = None
    preshared_key: Annotated[
        str | None, Field(description="Optional preshared key")
    ] = None

    validate_interface_properties_format = field_validator("interface_properties")(
        WireGuardNetworkBase.validate_interface_properties_format.__func__
    )

    @field_validator("network_cidr")
    @classmethod
    def validate_network_cidr_format(cls, v: str | None) -> str | None:
        """Validate network CIDR format and practical constraints."""
        return _validate_field(v, validate_network_cidr, "network_cidr")

    @field_validator("dns_servers")
    @classmethod
    def validate_dns_servers_format(cls, v: str | None) -> str | None:
        """Validate DNS servers format."""
        return _validate_field(v, validate_dns_servers, "dns_servers")

    @field_validator("mtu")
    @classmethod
    def validate_mtu_format(cls, v: int | None) -> int | None:
        """Validate MTU value."""
        return _validate_field(v, validate_mtu, "mtu")

    @field_validator("persistent_keepalive")
    @classmethod
    def validate_keepalive_format(cls, v: int | None) -> int | None:
        """Validate persistent keepalive value."""
        return _validate_field(v, validate_persistent_keepalive, "persistent_keepalive")

    @field_validator("preshared_key")
    @classmethod
    def validate_preshared_key_format(cls, v: str | None) -> str | None:
        """Validate preshared key format."""
        return _validate_preshared_key_format(v)


class WireGuardNetworkResponse(WireGuardNetworkBase):
    """Schema for WireGuard network response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime
    location_count: int = 0
    device_count: int = 0
