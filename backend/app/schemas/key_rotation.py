"""Pydantic schemas for key rotation operations."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, Field, field_validator


class MasterPasswordRotate(BaseModel):
    """Schema for rotating master password."""

    current_password: Annotated[
        str, Field(min_length=1, description="Current master password")
    ]
    new_password: Annotated[str, Field(min_length=1, description="New master password")]
    confirm_password: Annotated[
        str, Field(min_length=1, description="Confirm new master password")
    ]

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info: Any) -> str:
        """Validate that new password and confirmation match."""
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Passwords do not match")
        return v


class PasswordValidationResponse(BaseModel):
    """Schema for password validation response."""

    is_valid: bool
    strength: int
    score: int
    feedback: list[str]


class KeyRotationStatus(BaseModel):
    """Schema for key rotation status response."""

    total_networks: int
    total_devices: int
    rotated_networks: int
    rotated_devices: int
    failed_networks: int
    failed_devices: int
    errors: list[str]


class KeyRotationProgress(BaseModel):
    """Schema for key rotation progress updates."""

    stage: Annotated[str, Field(description="Current rotation stage")]
    progress: Annotated[
        float, Field(ge=0.0, le=1.0, description="Progress percentage (0.0-1.0)")
    ]
    message: Annotated[str, Field(description="Status message")]
    current_item: Annotated[str, Field(description="Currently processing item name")]
    items_completed: int
    total_items: int
