"""Pydantic schemas for location operations."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.utils.key_management import validate_wireguard_key_import
from app.utils.validation import (
    ValidationError,
    validate_host,
    validate_interface_properties,
)


class LocationBase(BaseModel):
    """Base schema for location."""

    network_id: str
    name: Annotated[str, Field(min_length=1, max_length=100)]
    description: str | None = None
    external_endpoint: Annotated[
        str | None,
        Field(max_length=255, description="External endpoint hostname or IP address"),
    ] = None
    internal_endpoint: Annotated[
        str | None,
        Field(max_length=255, description="Internal endpoint in format host:port"),
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

    @field_validator("external_endpoint", mode="before")
    @classmethod
    def validate_external_endpoint_format(cls, v: str | None) -> str | None:
        """Validate external endpoint format (hostname or IP, no port allowed)."""
        # Treat empty strings as None
        if v is None or v == "":
            return None

        try:
            # Validate as hostname or IP without port.
            validate_host(v)
            return v
        except Exception as e:
            raise ValueError(f"Invalid external endpoint: {e}") from e

    @field_validator("internal_endpoint")
    @classmethod
    def validate_internal_endpoint_format(cls, v: str | None) -> str | None:
        """Validate internal endpoint format."""
        if v is None:
            return v

        try:
            from app.utils.validation import validate_endpoint
            host, _ = validate_endpoint(v)
            return v
        except Exception as e:
            raise ValueError(f"Invalid internal endpoint: {e}") from e


class LocationCreate(LocationBase):
    """Schema for creating a location."""

    preshared_key: Annotated[
        str | None, Field(description="Optional preshared key")
    ] = None

    @field_validator("preshared_key")
    @classmethod
    def validate_preshared_key_format(cls, v: str | None) -> str | None:
        """Validate preshared key format."""
        if v is None:
            return v
        if isinstance(v, str) and v.strip() == "":
            return None
        try:
            return validate_wireguard_key_import(v, "preshared key")
        except Exception as e:
            raise ValueError(str(e)) from e


class LocationUpdate(BaseModel):
    """Schema for updating a location."""

    network_id: str | None = None
    name: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    description: str | None = None
    external_endpoint: Annotated[
        str | None,
        Field(max_length=255, description="External endpoint hostname or IP address"),
    ] = None
    internal_endpoint: Annotated[
        str | None,
        Field(max_length=255, description="Internal endpoint in format host:port"),
    ] = None
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

    # Reuse the same validator as LocationBase
    validate_external_endpoint_format = field_validator("external_endpoint", mode="before")(
        LocationBase.validate_external_endpoint_format.__func__
    )
    validate_internal_endpoint_format = field_validator("internal_endpoint")(
        LocationBase.validate_internal_endpoint_format.__func__
    )
    validate_interface_properties_format = field_validator("interface_properties")(
        LocationBase.validate_interface_properties_format.__func__
    )

    @field_validator("preshared_key")
    @classmethod
    def validate_preshared_key_format(cls, v: str | None) -> str | None:
        """Validate preshared key format."""
        if v is None:
            return v
        if isinstance(v, str) and v.strip() == "":
            return None
        try:
            return validate_wireguard_key_import(v, "preshared key")
        except Exception as e:
            raise ValueError(str(e)) from e


class LocationResponse(LocationBase):
    """Schema for location response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime
    network_name: str | None = None
    device_count: int = 0
