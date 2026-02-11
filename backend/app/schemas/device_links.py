"""Schemas for device-to-device link properties."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

from app.utils.key_management import validate_wireguard_key_import
from app.utils.validation import ValidationError, validate_peer_properties

PeerPropertyValue = str | int | bool | None


class DevicePeerLinkBase(BaseModel):
    """Base schema for directional device peer link properties."""

    from_device_id: Annotated[str, Field(min_length=1)]
    to_device_id: Annotated[str, Field(min_length=1)]
    properties: Annotated[dict[str, PeerPropertyValue] | None, Field()] = None

    @field_validator("properties")
    @classmethod
    def validate_properties(
        cls, value: dict[str, PeerPropertyValue] | None
    ) -> dict[str, PeerPropertyValue] | None:
        """Validate peer properties."""
        try:
            validate_peer_properties(value)
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc
        return value


class DevicePeerLinkCreate(DevicePeerLinkBase):
    """Create/update payload for device peer link properties."""

    preshared_key: str | None = None

    @field_validator("preshared_key")
    @classmethod
    def validate_preshared_key(cls, value: str | None) -> str | None:
        """Validate WireGuard preshared key format."""
        if value is None:
            return None
        return validate_wireguard_key_import(value, "preshared key")


class DevicePeerLinkResponse(DevicePeerLinkBase):
    """Response schema for device peer link properties."""

    id: str
    network_id: str
    created_at: datetime
    updated_at: datetime
