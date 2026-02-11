"""Router for operational settings management endpoints."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import select

from app.config import settings as app_settings
from app.database.connection import get_db
from app.database.models import OperationalSetting
from app.middleware.auth import get_master_session, require_master_session
from app.utils.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


class OperationalSettingsUpdate(BaseModel):
    """Request schema for updating operational settings."""

    # Request hardening settings
    max_request_size: int | None = None
    request_timeout: int | None = None
    max_json_depth: int | None = None
    max_string_length: int | None = None
    max_items_per_array: int | None = None

    # Rate limiting settings
    rate_limit_api_key_window: int | None = None
    rate_limit_api_key_max_requests: int | None = None
    rate_limit_ip_window: int | None = None
    rate_limit_ip_max_requests: int | None = None

    # Audit settings
    audit_retention_days: int | None = None
    audit_export_batch_size: int | None = None

    # Master password cache settings
    master_password_ttl_hours: float | None = None
    master_password_idle_timeout_minutes: float | None = None
    master_password_per_user_session: bool | None = None

    # Trusted proxy settings
    trusted_proxies: str | None = None

    # CORS settings
    cors_origins: str | None = None
    cors_allow_credentials: bool | None = None

    # Logo settings
    logo_bg_color: str | None = None
    logo_text: str | None = None
    app_name: str | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("max_request_size")
    def validate_max_request_size(cls, v: int | None) -> int | None:
        """Validate max request size."""
        if v is None:
            return v
        if v < 1024:
            raise ValueError("max_request_size must be at least 1024 bytes (1KB)")
        if v > 104857600:  # 100MB
            raise ValueError("max_request_size must not exceed 104857600 bytes (100MB)")
        return v

    @field_validator("request_timeout")
    def validate_request_timeout(cls, v: int | None) -> int | None:
        """Validate request timeout."""
        if v is None:
            return v
        if v < 1:
            raise ValueError("request_timeout must be at least 1 second")
        if v > 300:
            raise ValueError("request_timeout must not exceed 300 seconds (5 minutes)")
        return v

    @field_validator("max_json_depth")
    def validate_max_json_depth(cls, v: int | None) -> int | None:
        """Validate max JSON depth."""
        if v is None:
            return v
        if v < 1:
            raise ValueError("max_json_depth must be at least 1")
        if v > 100:
            raise ValueError("max_json_depth must not exceed 100")
        return v

    @field_validator("max_string_length")
    def validate_max_string_length(cls, v: int | None) -> int | None:
        """Validate max string length."""
        if v is None:
            return v
        if v < 100:
            raise ValueError("max_string_length must be at least 100")
        if v > 1000000:
            raise ValueError("max_string_length must not exceed 1000000")
        return v

    @field_validator("max_items_per_array")
    def validate_max_items_per_array(cls, v: int | None) -> int | None:
        """Validate max items per array."""
        if v is None:
            return v
        if v < 1:
            raise ValueError("max_items_per_array must be at least 1")
        if v > 100000:
            raise ValueError("max_items_per_array must not exceed 100000")
        return v

    @field_validator("rate_limit_api_key_window")
    def validate_rate_limit_api_key_window(cls, v: int | None) -> int | None:
        """Validate rate limit API key window."""
        if v is None:
            return v
        if v < 1:
            raise ValueError("rate_limit_api_key_window must be at least 1 second")
        if v > 86400:
            raise ValueError("rate_limit_api_key_window must not exceed 86400 seconds (24 hours)")
        return v

    @field_validator("rate_limit_api_key_max_requests")
    def validate_rate_limit_api_key_max_requests(cls, v: int | None) -> int | None:
        """Validate rate limit API key max requests."""
        if v is None:
            return v
        if v < 1:
            raise ValueError("rate_limit_api_key_max_requests must be at least 1")
        if v > 1000000:
            raise ValueError("rate_limit_api_key_max_requests must not exceed 1000000")
        return v

    @field_validator("rate_limit_ip_window")
    def validate_rate_limit_ip_window(cls, v: int | None) -> int | None:
        """Validate rate limit IP window."""
        if v is None:
            return v
        if v < 1:
            raise ValueError("rate_limit_ip_window must be at least 1 second")
        if v > 86400:
            raise ValueError("rate_limit_ip_window must not exceed 86400 seconds (24 hours)")
        return v

    @field_validator("rate_limit_ip_max_requests")
    def validate_rate_limit_ip_max_requests(cls, v: int | None) -> int | None:
        """Validate rate limit IP max requests."""
        if v is None:
            return v
        if v < 1:
            raise ValueError("rate_limit_ip_max_requests must be at least 1")
        if v > 1000000:
            raise ValueError("rate_limit_ip_max_requests must not exceed 1000000")
        return v

    @field_validator("audit_retention_days")
    def validate_audit_retention_days(cls, v: int | None) -> int | None:
        """Validate audit retention days."""
        if v is None:
            return v
        if v < 1:
            raise ValueError("audit_retention_days must be at least 1 day")
        if v > 3650:  # 10 years
            raise ValueError("audit_retention_days must not exceed 3650 days (10 years)")
        return v

    @field_validator("audit_export_batch_size")
    def validate_audit_export_batch_size(cls, v: int | None) -> int | None:
        """Validate audit export batch size."""
        if v is None:
            return v
        if v < 100:
            raise ValueError("audit_export_batch_size must be at least 100")
        if v > 1000000:
            raise ValueError("audit_export_batch_size must not exceed 1000000")
        return v

    @field_validator("master_password_ttl_hours")
    def validate_master_password_ttl_hours(cls, v: float | None) -> float | None:
        """Validate master password TTL hours."""
        if v is None:
            return v
        if v < 0.1:
            raise ValueError("master_password_ttl_hours must be at least 0.1 hours (6 minutes)")
        if v > 24.0:
            raise ValueError("master_password_ttl_hours must not exceed 24 hours")
        return v

    @field_validator("master_password_idle_timeout_minutes")
    def validate_master_password_idle_timeout_minutes(cls, v: float | None) -> float | None:
        """Validate master password idle timeout minutes."""
        if v is None:
            return v
        if v < 1.0:
            raise ValueError("master_password_idle_timeout_minutes must be at least 1 minute")
        if v > 1440.0:  # 24 hours
            raise ValueError("master_password_idle_timeout_minutes must not exceed 1440 minutes (24 hours)")
        return v

    @field_validator("trusted_proxies")
    def validate_trusted_proxies(cls, v: str | None) -> str | None:
        """Validate trusted proxies format."""
        if v is None or v == "":
            return ""
        proxies = [p.strip() for p in v.split(",") if p.strip()]
        for proxy in proxies:
            # Check if it's a valid IP or CIDR
            ip_cidr_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(?:/\d{1,3})?$|::1$|^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}(?:/\d{1,3})?$'
            if not re.match(ip_cidr_pattern, proxy):
                raise ValueError(f"Invalid IP or CIDR format: {proxy}")
        return ", ".join(proxies)

    @field_validator("cors_origins")
    def validate_cors_origins(cls, v: str | None) -> str | None:
        """Validate CORS origins format."""
        if v is None or v == "":
            return ""
        origins = [o.strip() for o in v.split(",") if o.strip()]
        for origin in origins:
            # Validate URL format
            url_pattern = r'^https?://(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}(?::\d{1,5})?(?:/.*)?$|^http://localhost(?::\d{1,5})?$|^https://localhost(?::\d{1,5})?$|^http://127\.0\.0\.1(?::\d{1,5})?$'
            if not re.match(url_pattern, origin):
                raise ValueError(f"Invalid origin URL format: {origin}")
        return ",".join(origins)

    @field_validator("logo_bg_color")
    def validate_logo_bg_color(cls, v: str | None) -> str | None:
        """Validate logo background color as hex color."""
        if v is None or v == "":
            return ""
        # Check if it's a valid hex color (3, 4, 6, or 8 characters)
        hex_pattern = r'^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{4}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})$'
        if not re.match(hex_pattern, v):
            raise ValueError("logo_bg_color must be a valid hex color (e.g., #FF5733, #F53)")
        return v

    @field_validator("logo_text")
    def validate_logo_text(cls, v: str | None) -> str | None:
        """Validate logo text length and content."""
        if v is None:
            return v
        if len(v) == 0:
            raise ValueError("logo_text must be 1-3 characters long")
        if len(v) > 3:
            raise ValueError("logo_text must be 1-3 characters long")
        if not v.isalnum():
            raise ValueError("logo_text must contain only alphanumeric characters")
        return v.upper()

    @field_validator("app_name")
    def validate_app_name(cls, v: str | None) -> str | None:
        """Validate app name length and content."""
        if v is None:
            return v
        if len(v) == 0:
            raise ValueError("app_name must be at least 1 character long")
        if len(v) > 100:
            raise ValueError("app_name must not exceed 100 characters")
        return v


class OperationalSettingsResponse(BaseModel):
    """Response schema for operational settings."""

    # Request hardening settings
    max_request_size: int
    request_timeout: int
    max_json_depth: int
    max_string_length: int
    max_items_per_array: int

    # Rate limiting settings
    rate_limit_api_key_window: int
    rate_limit_api_key_max_requests: int
    rate_limit_ip_window: int
    rate_limit_ip_max_requests: int

    # Audit settings
    audit_retention_days: int
    audit_export_batch_size: int

    # Master password cache settings
    master_password_ttl_hours: float
    master_password_idle_timeout_minutes: float
    master_password_per_user_session: bool

    # Trusted proxy settings
    trusted_proxies: str

    # CORS settings
    cors_origins: str
    cors_allow_credentials: bool

    # Logo settings
    logo_bg_color: str
    logo_text: str
    app_name: str

    model_config = ConfigDict(from_attributes=True)


router = APIRouter(prefix="/settings", tags=["settings"])


async def get_settings_from_db(db: AsyncSession) -> dict[str, Any]:
    """Get settings from database, falling back to app settings."""
    result = await db.execute(select(OperationalSetting))
    db_settings = result.scalars().all()

    settings_dict: dict[str, Any] = {}
    for db_setting in db_settings:
        settings_dict[db_setting.key] = db_setting.value

    # Helper function to get setting with fallback
    def get_setting(key: str, default: Any, expected_type: type) -> Any:
        if key in settings_dict:
            try:
                return expected_type(settings_dict[key])
            except (ValueError, TypeError):
                logger.warning(f"Invalid value for {key}, using default", extra={"key": key})
                return default
        return default

    return {
        # Request hardening settings
        "max_request_size": get_setting("max_request_size", app_settings.max_request_size, int),
        "request_timeout": get_setting("request_timeout", app_settings.request_timeout, int),
        "max_json_depth": get_setting("max_json_depth", app_settings.max_json_depth, int),
        "max_string_length": get_setting("max_string_length", app_settings.max_string_length, int),
        "max_items_per_array": get_setting("max_items_per_array", app_settings.max_items_per_array, int),
        # Rate limiting settings
        "rate_limit_api_key_window": get_setting("rate_limit_api_key_window", app_settings.rate_limit_api_key_window, int),
        "rate_limit_api_key_max_requests": get_setting("rate_limit_api_key_max_requests", app_settings.rate_limit_api_key_max_requests, int),
        "rate_limit_ip_window": get_setting("rate_limit_ip_window", app_settings.rate_limit_ip_window, int),
        "rate_limit_ip_max_requests": get_setting("rate_limit_ip_max_requests", app_settings.rate_limit_ip_max_requests, int),
        # Audit settings
        "audit_retention_days": get_setting("audit_retention_days", app_settings.audit_retention_days, int),
        "audit_export_batch_size": get_setting("audit_export_batch_size", app_settings.audit_export_batch_size, int),
        # Master password cache settings
        "master_password_ttl_hours": get_setting("master_password_ttl_hours", app_settings.master_password_ttl_hours, float),
        "master_password_idle_timeout_minutes": get_setting("master_password_idle_timeout_minutes", app_settings.master_password_idle_timeout_minutes, float),
        "master_password_per_user_session": get_setting("master_password_per_user_session", app_settings.master_password_per_user_session, bool),
        # Trusted proxy settings
        "trusted_proxies": get_setting("trusted_proxies", app_settings.trusted_proxies, str),
        # CORS settings
        "cors_origins": get_setting("cors_origins", app_settings.cors_origins, str),
        "cors_allow_credentials": get_setting("cors_allow_credentials", app_settings.cors_allow_credentials, bool),
        # Logo settings
        "logo_bg_color": get_setting("logo_bg_color", "#1e3a8a", str),
        "logo_text": get_setting("logo_text", "WG", str),
        "app_name": get_setting("app_name", "WireGuard Mesh Manager", str),
    }


@router.get(
    "",
    response_model=OperationalSettingsResponse,
    summary="Get operational settings",
    description="Retrieve current operational settings from the database or fallback to defaults.",
)
async def get_operational_settings(
    db: AsyncSession = Depends(get_db),
    _: Any = Depends(get_master_session),  # Optional authentication for UI customization
) -> OperationalSettingsResponse:
    """Get operational settings."""
    settings_dict = await get_settings_from_db(db)
    return OperationalSettingsResponse(**settings_dict)


@router.patch(
    "",
    response_model=OperationalSettingsResponse,
    summary="Update operational settings",
    description="Update operational settings. Only provided fields will be updated.",
    status_code=status.HTTP_200_OK,
)
async def update_operational_settings(
    settings_update: OperationalSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    actor: str = Depends(require_master_session),
) -> OperationalSettingsResponse:
    """Update operational settings."""
    # Get current settings
    current_settings = await get_settings_from_db(db)

    # Update only non-None fields
    update_dict = settings_update.model_dump(exclude_unset=True)
    if not update_dict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update",
        )

    # Update database
    for key, value in update_dict.items():
        result = await db.execute(select(OperationalSetting).where(OperationalSetting.key == key))
        db_setting = result.scalar_one_or_none()

        if db_setting:
            db_setting.value = str(value)
        else:
            db_setting = OperationalSetting(key=key, value=str(value))
            db.add(db_setting)

    await db.commit()

    logger.info(
        "Operational settings updated",
        extra={
            "actor": actor,
            "updated_fields": list(update_dict.keys()),
        },
    )

    # Return updated settings
    updated_settings = await get_settings_from_db(db)
    return OperationalSettingsResponse(**updated_settings)
