"""Pydantic schemas for device management."""

from __future__ import annotations

import base64
import binascii
from ipaddress import IPv4Address
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.utils.validation import (
    ValidationError,
    validate_host,
    validate_interface_properties,
    validate_port,
)


class DeviceBase(BaseModel):
    """Base device schema with common fields."""

    name: Annotated[str, Field(min_length=1, max_length=100)]
    description: Annotated[str | None, Field(max_length=1000)] = None
    enabled: bool = True
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


class DeviceCreate(DeviceBase):
    """Schema for creating a new device."""

    network_id: str
    location_id: str
    wireguard_ip: str | None = None
    external_endpoint_host: str | None = None
    external_endpoint_port: int | None = None
    internal_endpoint_host: str | None = None
    internal_endpoint_port: int | None = None
    public_key: Annotated[str | None, Field(min_length=40, max_length=56)] = None
    private_key: Annotated[str | None, Field(min_length=40, max_length=56)] = None
    preshared_key: str | None = None

    @field_validator("wireguard_ip")
    @classmethod
    def validate_wireguard_ip(cls, v: str | None) -> str | None:
        """Validate IPv4 address format."""
        if v is None:
            return v
        try:
            IPv4Address(v)
            return v
        except ValueError as e:
            raise ValueError(f"Invalid IPv4 address: {v}") from e

    @field_validator("external_endpoint_host", "internal_endpoint_host")
    @classmethod
    def validate_endpoint_host(cls, v: str | None) -> str | None:
        """Validate endpoint host format (hostname or IP)."""
        if v is None:
            return None
        trimmed = v.strip()
        if trimmed == "":
            return None
        try:
            validate_host(trimmed)
            return trimmed
        except ValidationError as e:
            raise ValueError(str(e)) from e

    @field_validator("external_endpoint_port", "internal_endpoint_port", mode="before")
    @classmethod
    def validate_endpoint_port(cls, v: int | str | None) -> int | None:
        """Validate endpoint port range."""
        if v is None:
            return None
        if isinstance(v, bool):
            raise ValueError("Port must be an integer between 1 and 65535")
        if isinstance(v, str):
            trimmed = v.strip()
            if trimmed == "":
                return None
            v = trimmed
        if isinstance(v, float):
            if not v.is_integer():
                raise ValueError("Port must be an integer between 1 and 65535")
            v = int(v)
        try:
            return validate_port(int(v))
        except (TypeError, ValueError, ValidationError) as e:
            raise ValueError("Port must be an integer between 1 and 65535") from e

    @model_validator(mode="after")
    def validate_endpoint_pairs(self) -> "DeviceCreate":
        """Validate endpoint host/port pairing rules."""
        if self.external_endpoint_host and self.external_endpoint_port is None:
            raise ValueError("External endpoint host requires a port")
        if (
            self.internal_endpoint_host is None
            and self.internal_endpoint_port is not None
        ) or (
            self.internal_endpoint_host is not None
            and self.internal_endpoint_port is None
        ):
            raise ValueError("Internal endpoint requires both host and port")

        # Require at least one port to be provided (internal or external)
        has_external_port = self.external_endpoint_port is not None
        has_internal_port = self.internal_endpoint_port is not None

        if not has_external_port and not has_internal_port:
            raise ValueError("At least one port (internal or external) must be provided")

        return self

    @field_validator("public_key", "private_key", "preshared_key")
    @classmethod
    def validate_wireguard_keys(cls, v: str | None) -> str | None:
        """Validate WireGuard key format."""
        if v is None:
            return v
        allowed_lengths = {40, 44, 45, 56}
        if len(v) not in allowed_lengths:
            raise ValueError("WireGuard key must be 44, 45, or 56 characters")
        try:
            try:
                base64.b64decode(v, validate=True)
            except (ValueError, binascii.Error):
                if len(v) == 45 and v.endswith("="):
                    base64.b64decode(v[:-1], validate=True)
                else:
                    raise
            return v
        except (ValueError, binascii.Error) as e:
            raise ValueError(
                "Invalid WireGuard key format - must be base64 encoded"
            ) from e


class DeviceUpdate(BaseModel):
    """Schema for updating a device."""

    name: Annotated[str | None, Field(min_length=1, max_length=100)] = None
    description: Annotated[str | None, Field(max_length=1000)] = None
    wireguard_ip: str | None = None
    external_endpoint_host: str | None = None
    external_endpoint_port: int | None = None
    internal_endpoint_host: str | None = None
    internal_endpoint_port: int | None = None
    public_key: Annotated[str | None, Field(min_length=40, max_length=56)] = None
    private_key: Annotated[str | None, Field(min_length=40, max_length=56)] = None
    preshared_key: str | None = None
    enabled: bool | None = None
    location_id: str | None = None
    interface_properties: (
        Annotated[
            dict[str, Any],
            Field(
                description="Additional WireGuard interface properties as key-value pairs"
            ),
        ]
        | None
    ) = None

    validate_interface_properties_format = field_validator("interface_properties")(
        DeviceBase.validate_interface_properties_format.__func__
    )

    @field_validator("wireguard_ip")
    @classmethod
    def validate_wireguard_ip(cls, v: str | None) -> str | None:
        """Validate IPv4 address format."""
        if v is None:
            return v
        try:
            IPv4Address(v)
            return v
        except ValueError as e:
            raise ValueError(f"Invalid IPv4 address: {v}") from e

    @field_validator("external_endpoint_host", "internal_endpoint_host")
    @classmethod
    def validate_endpoint_host(cls, v: str | None) -> str | None:
        """Validate endpoint host format (hostname or IP)."""
        if v is None:
            return None
        trimmed = v.strip()
        if trimmed == "":
            return None
        try:
            validate_host(trimmed)
            return trimmed
        except ValidationError as e:
            raise ValueError(str(e)) from e

    @field_validator("external_endpoint_port", "internal_endpoint_port", mode="before")
    @classmethod
    def validate_endpoint_port(cls, v: int | str | None) -> int | None:
        """Validate endpoint port range."""
        if v is None:
            return None
        if isinstance(v, bool):
            raise ValueError("Port must be an integer between 1 and 65535")
        if isinstance(v, str):
            trimmed = v.strip()
            if trimmed == "":
                return None
            v = trimmed
        if isinstance(v, float):
            if not v.is_integer():
                raise ValueError("Port must be an integer between 1 and 65535")
            v = int(v)
        try:
            return validate_port(int(v))
        except (TypeError, ValueError, ValidationError) as e:
            raise ValueError("Port must be an integer between 1 and 65535") from e

    @model_validator(mode="after")
    def validate_endpoint_pairs(self) -> "DeviceUpdate":
        """Validate endpoint host/port pairing rules when provided."""
        fields_set = self.model_fields_set
        external_set = {
            "external_endpoint_host",
            "external_endpoint_port",
        } & fields_set
        internal_set = {
            "internal_endpoint_host",
            "internal_endpoint_port",
        } & fields_set

        if external_set and self.external_endpoint_host and self.external_endpoint_port is None:
            raise ValueError("External endpoint host requires a port")

        if internal_set:
            if (
                self.internal_endpoint_host is None
                and self.internal_endpoint_port is not None
            ) or (
                self.internal_endpoint_host is not None
                and self.internal_endpoint_port is None
            ):
                raise ValueError("Internal endpoint requires both host and port")

        # If any endpoint field is being updated, ensure at least one port is provided
        # after the update
        if external_set or internal_set:
            # Check what the values will be after update
            new_external_port = (
                self.external_endpoint_port
                if "external_endpoint_port" in fields_set
                else None
            )
            new_internal_port = (
                self.internal_endpoint_port
                if "internal_endpoint_port" in fields_set
                else None
            )

            # Only validate if at least one port field is being explicitly set
            # We don't check the original values because we don't have access to them here
            if new_external_port is not None or new_internal_port is not None:
                # Check if at least one port will be present
                if new_external_port is None and new_internal_port is None:
                    # Both being set to None explicitly
                    raise ValueError(
                        "At least one port (internal or external) must be provided"
                    )

        return self

    @field_validator("public_key", "private_key", "preshared_key")
    @classmethod
    def validate_wireguard_keys(cls, v: str | None) -> str | None:
        """Validate WireGuard key format."""
        if v is None:
            return v
        allowed_lengths = {40, 44, 45, 56}
        if len(v) not in allowed_lengths:
            raise ValueError("WireGuard key must be 44, 45, or 56 characters")
        try:
            try:
                base64.b64decode(v, validate=True)
            except (ValueError, binascii.Error):
                if len(v) == 45 and v.endswith("="):
                    base64.b64decode(v[:-1], validate=True)
                else:
                    raise
            return v
        except (ValueError, binascii.Error) as e:
            raise ValueError(
                "Invalid WireGuard key format - must be base64 encoded"
            ) from e


class DeviceResponse(DeviceBase):
    """Schema for device responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    network_id: str
    location_id: str
    wireguard_ip: str
    external_endpoint_host: str | None = None
    external_endpoint_port: int | None = None
    internal_endpoint_host: str | None = None
    internal_endpoint_port: int | None = None
    public_key: str
    preshared_key: str | None
    created_at: str
    updated_at: str
    network_name: str | None = None
    location_name: str | None = None
    location_external_endpoint: str | None = None
    api_key: str | None = None
    api_key_last_used: str | None = None


class DeviceAllocationResponse(BaseModel):
    """Schema for IP allocation response."""

    allocated_ip: str
    available_ips: list[str]


class DeviceWithConfig(DeviceResponse):
    """Device response including WireGuard configuration."""

    config: dict[str, Any] | None = None


class APIKeyBase(BaseModel):
    """Base API key schema with common fields."""

    name: Annotated[str, Field(min_length=1, max_length=100)]
    allowed_ip_ranges: Annotated[str | None, Field(max_length=1000)] = None
    enabled: bool = True
    expires_at: str | None = None


class APIKeyCreate(APIKeyBase):
    """Schema for creating a new API key."""

    device_id: str

    @field_validator("allowed_ip_ranges")
    @classmethod
    def validate_ip_ranges(cls, v: str | None) -> str | None:
        """Validate IP ranges format."""
        if v is None:
            return v
        from app.utils.api_key import validate_ip_ranges

        return validate_ip_ranges(v)


class APIKeyUpdate(BaseModel):
    """Schema for updating an API key."""

    name: Annotated[str | None, Field(min_length=1, max_length=100)] = None
    allowed_ip_ranges: Annotated[str | None, Field(min_length=1, max_length=1000)] = (
        None
    )
    enabled: bool | None = None
    expires_at: str | None = None

    @field_validator("allowed_ip_ranges")
    @classmethod
    def validate_ip_ranges(cls, v: str | None) -> str | None:
        """Validate IP ranges format."""
        if v is None:
            return v
        from app.utils.api_key import validate_ip_ranges

        return validate_ip_ranges(v)


class APIKeyResponse(APIKeyBase):
    """Schema for API key responses."""

    id: str
    device_id: str
    network_id: str
    last_used_at: str | None = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class APIKeyCreateResponse(BaseModel):
    """Schema for API key creation response."""

    api_key: APIKeyResponse
    # The actual key value - only returned once during creation
    key_value: str


class APIKeyRotateResponse(BaseModel):
    """Schema for API key rotation response."""

    old_key: APIKeyResponse
    new_key: APIKeyCreateResponse


class KeyGenerationMethod(BaseModel):
    """Schema for key generation method."""

    method: Literal["cli", "crypto"] = Field(
        description="Method used to generate keys: 'cli' uses WireGuard tools, 'crypto' uses Python cryptography"
    )


class WireGuardKeyPairResponse(BaseModel):
    """Schema for WireGuard key pair generation response."""

    private_key: str = Field(description="The generated private key (base64-encoded)")
    public_key: str = Field(description="The generated public key (base64-encoded)")
    method: Literal["cli", "crypto"] = Field(
        description="Method used to generate the keys"
    )


class WireGuardPresharedKeyResponse(BaseModel):
    """Schema for WireGuard preshared key generation response."""

    preshared_key: str = Field(
        description="The generated preshared key (base64-encoded)"
    )


class DeviceKeysRegenerateResponse(BaseModel):
    """Schema for device key regeneration response."""

    id: str
    name: str
    public_key: str
    private_key_encrypted: bool = Field(
        description="Whether the private key is encrypted in storage"
    )
