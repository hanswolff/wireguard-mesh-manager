"""API routes for device management.

Self-service configuration endpoints authenticate via per-device API keys and
IP allowlists, while admin configuration endpoints require a master session
token and an unlocked master password.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

import sqlalchemy.ext.asyncio  # noqa: TC002
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse

from app.database.connection import get_db
from app.middleware.auth import require_master_session
from app.routers.utils import (
    extract_device_auth_info,
    get_audit_service,
    get_client_actor,
    raise_request_validation_error,
    validate_device_access,
)
from app.schemas.device_config import DeviceConfigResponse
from app.schemas.devices import (
    APIKeyCreate,
    APIKeyCreateResponse,
    APIKeyResponse,
    DeviceAllocationResponse,
    DeviceCreate,
    DeviceKeysRegenerateResponse,
    DeviceResponse,
    DeviceUpdate,
    KeyGenerationMethod,
    WireGuardKeyPairResponse,
    WireGuardPresharedKeyResponse,
)
from app.services.audit import AuditService
from app.services.api_key import APIKeyService
from app.services.device_config import DeviceConfigService
from app.services.devices import DeviceService
from app.utils.api_key import (
    APIKeyNotFoundError,
    DeviceNotFoundError,
    compute_api_key_fingerprint,
    generate_api_key,
)
from app.utils import key_management
from app.utils.key_management import (
    decrypt_device_dek_from_json,
    encrypt_device_dek_with_master,
    generate_device_dek,
    import_wireguard_private_key_with_dek,
)
from app.utils.master_password import get_master_password, get_master_password_cache

if TYPE_CHECKING:
    pass

AsyncSession: type = sqlalchemy.ext.asyncio.AsyncSession

router = APIRouter(tags=["devices"])


def _device_validation_field(message: str) -> str | None:
    message_lower = message.lower()
    if "wireguard ip" in message_lower or "ip " in message_lower:
        if "network cidr" in message_lower or "invalid ip" in message_lower or "already allocated" in message_lower or "available ip" in message_lower:
            return "wireguard_ip"
    if "public key" in message_lower:
        return "public_key"
    if "private key" in message_lower:
        return "private_key"
    if "preshared" in message_lower:
        return "preshared_key"
    if "external endpoint host" in message_lower:
        return "external_endpoint_host"
    if "external endpoint port" in message_lower or "external port" in message_lower:
        return "external_endpoint_port"
    if "external endpoint" in message_lower:
        return "external_endpoint_host"
    if "internal endpoint host" in message_lower:
        return "internal_endpoint_host"
    if "internal endpoint port" in message_lower or "internal port" in message_lower:
        return "internal_endpoint_port"
    if "internal endpoint" in message_lower:
        return "internal_endpoint_host"
    if "location" in message_lower:
        return "location_id"
    if "network" in message_lower:
        return "network_id"
    return None


def get_device_service(db: Annotated[AsyncSession, Depends(get_db)]) -> DeviceService:
    """Get device service instance."""
    return DeviceService(db)


def get_api_key_service(db: Annotated[AsyncSession, Depends(get_db)]) -> APIKeyService:
    """Get API key service instance."""
    return APIKeyService(db)


def _device_to_response(device: Any) -> DeviceResponse:
    """Convert device model to response with additional info."""
    # Get API key information
    api_key = None
    api_key_last_used = None

    if hasattr(device, "api_keys") and device.api_keys:
        for key in device.api_keys:
            if key.enabled:
                api_key = "set"
                if key.last_used_at:
                    api_key_last_used = key.last_used_at.isoformat()
                break

    return DeviceResponse(
        id=device.id,
        name=device.name,
        description=device.description,
        enabled=device.enabled,
        network_id=device.network_id,
        location_id=device.location_id,
        wireguard_ip=device.wireguard_ip,
        external_endpoint_host=getattr(device, "external_endpoint_host", None),
        external_endpoint_port=getattr(device, "external_endpoint_port", None),
        internal_endpoint_host=getattr(device, "internal_endpoint_host", None),
        internal_endpoint_port=getattr(device, "internal_endpoint_port", None),
        public_key=device.public_key,
        preshared_key=None,  # Don't expose encrypted key material
        interface_properties=getattr(device, "interface_properties", None),
        created_at=device.created_at.isoformat() if device.created_at else "",
        updated_at=device.updated_at.isoformat() if device.updated_at else "",
        network_name=device.network.name if device.network else None,
        location_name=device.location.name if device.location else None,
        location_external_endpoint=device.location.external_endpoint if device.location else None,
        api_key=api_key,
        api_key_last_used=api_key_last_used,
    )


def _api_key_to_response(api_key: Any) -> APIKeyResponse:
    """Convert API key model to response schema."""
    return APIKeyResponse(
        id=api_key.id,
        name=api_key.name,
        allowed_ip_ranges=api_key.allowed_ip_ranges,
        enabled=api_key.enabled,
        expires_at=api_key.expires_at.isoformat() if api_key.expires_at else None,
        last_used_at=api_key.last_used_at.isoformat() if api_key.last_used_at else None,
        created_at=api_key.created_at.isoformat() if api_key.created_at else "",
        updated_at=api_key.updated_at.isoformat() if api_key.updated_at else "",
        device_id=api_key.device_id,
        network_id=api_key.network_id,
    )


@router.get("/", response_model=list[DeviceResponse])
async def list_devices(
    _: Annotated[None, Depends(require_master_session)],
    service: Annotated[DeviceService, Depends(get_device_service)],
    network_id: Annotated[str | None, Query(description="Filter by network ID")] = None,
    search: Annotated[str | None, Query(description="Search by device name")] = None,
    location_id: Annotated[str | None, Query(description="Filter by location ID")] = None,
    enabled: Annotated[bool | None, Query(description="Filter by enabled status")] = None,
) -> list[DeviceResponse]:
    """List all devices, optionally filtered by network ID, search, location, or enabled status."""
    if network_id:
        devices = await service.get_devices_by_network(
            network_id,
            search=search,
            location_id=location_id,
            enabled=enabled,
        )
    else:
        devices = await service.list_devices(
            search=search,
            location_id=location_id,
            enabled=enabled,
        )
    return [_device_to_response(device) for device in devices]


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: str,
    service: Annotated[DeviceService, Depends(get_device_service)],
    _: Annotated[None, Depends(require_master_session)],
) -> DeviceResponse:
    """Get a specific device by ID."""
    try:
        device = await service.get_device(device_id)
        return _device_to_response(device)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get("/network/{network_id}", response_model=list[DeviceResponse])
async def get_devices_by_network(
    network_id: str,
    service: Annotated[DeviceService, Depends(get_device_service)],
    _: Annotated[None, Depends(require_master_session)],
) -> list[DeviceResponse]:
    """Get all devices in a specific network."""
    try:
        devices = await service.get_devices_by_network(network_id)
        return [_device_to_response(device) for device in devices]
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get(
    "/network/{network_id}/available-ips", response_model=DeviceAllocationResponse
)
async def get_available_ips(
    network_id: str,
    service: Annotated[DeviceService, Depends(get_device_service)],
    _: Annotated[None, Depends(require_master_session)],
) -> DeviceAllocationResponse:
    """Get available IP addresses for a network."""
    try:
        available_ips = await service.get_available_ips(network_id)
        # Allocate first available IP for preview
        allocated_ip = available_ips[0] if available_ips else None

        allocated_ip = allocated_ip or ""
        return DeviceAllocationResponse(
            allocated_ip=allocated_ip,
            available_ips=available_ips[:10],  # Return first 10 for UI
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post("/", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
async def create_device(
    device_data: DeviceCreate,
    service: Annotated[DeviceService, Depends(get_device_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    request: Request,
    _: Annotated[None, Depends(require_master_session)],
) -> DeviceResponse:
    """Create a new device."""
    actor = get_client_actor(request)
    session = getattr(request.state, "master_session", None)

    try:
        device = await service.create_device(
            device_data, session_id=session.session_id if session else None
        )

        # Log the creation event
        await audit_service.log_event(
            network_id=device.network_id,
            actor=actor,
            action="CREATE",
            resource_type="device",
            resource_id=device.id,
            details={
                "resource_name": device.name,
                "location_id": device.location_id,
                "wireguard_ip": device.wireguard_ip,
                "description": device_data.description,
            },
        )

        return _device_to_response(device)

    except ValueError as e:
        message = str(e)
        if "master password" in message.lower():
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Master password must be unlocked to create devices",
            ) from e
        raise_request_validation_error(message, _device_validation_field(message))


@router.put("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: str,
    device_data: DeviceUpdate,
    service: Annotated[DeviceService, Depends(get_device_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    request: Request,
    _: Annotated[None, Depends(require_master_session)],
) -> DeviceResponse:
    """Update a device."""
    actor = get_client_actor(request)
    session = getattr(request.state, "master_session", None)

    try:
        # Get old device for audit trail
        old_device = await service.get_device(device_id)

        # Update the device
        device = await service.update_device(
            device_id,
            device_data,
            session_id=session.session_id if session else None,
        )

        # Log the update event with changes
        changes = {}
        update_data = device_data.model_dump(exclude_unset=True)
        for key, new_value in update_data.items():
            old_value = getattr(old_device, key, None)
            if old_value != new_value:
                changes[key] = {"old": old_value, "new": new_value}

        if changes:  # Only log if there were actual changes
            await audit_service.log_admin_action(
                network_id=device.network_id,
                admin_actor=actor,
                action="UPDATE",
                resource_type="device",
                resource_id=device_id,
                resource_name=device.name,
                changes=changes,
            )

        return _device_to_response(device)

    except ValueError as e:
        message = str(e)
        if "master password" in message.lower():
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Master password must be unlocked to update devices",
            ) from e
        raise_request_validation_error(message, _device_validation_field(message))


@router.delete("/{device_id}")
async def delete_device(
    device_id: str,
    service: Annotated[DeviceService, Depends(get_device_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    request: Request,
    _: Annotated[None, Depends(require_master_session)],
) -> dict[str, str]:
    """Delete a device."""
    actor = get_client_actor(request)

    try:
        device = await service.get_device(device_id)

        # Log the deletion event before deleting
        await audit_service.log_event(
            network_id=device.network_id,
            actor=actor,
            action="DELETE",
            resource_type="device",
            resource_id=device_id,
            details={
                "resource_name": device.name,
                "wireguard_ip": device.wireguard_ip,
                "location_id": device.location_id,
            },
        )

        await service.delete_device(device_id)
        return {"message": f"Device '{device.name}' deleted successfully"}

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


def get_device_config_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeviceConfigService:
    """Get device config service instance."""
    return DeviceConfigService(db)


def _validate_config_request(format_type: str, platform: str | None) -> None:
    """Validate device config request parameters."""
    allowed_formats = {"wg", "json", "mobile"}
    if format_type not in allowed_formats:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format '{format_type}'",
        )
    if format_type == "mobile" and not platform:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mobile configuration requires a platform value",
        )


async def _generate_device_config_response(
    device_id: str,
    format_type: str = "wg",
    platform: str | None = None,
    *,
    config_service: DeviceConfigService,
    audit_service: AuditService,
    auth_info,
) -> DeviceConfigResponse:
    """Generate device configuration response with authentication and logging.

    Args:
        device_id: ID of the device
        format_type: Configuration format ('wg', 'json', 'mobile')
        platform: Mobile platform for optimized config
        config_service: Device configuration service
        audit_service: Audit logging service
        auth_info: Authentication information

    Returns:
        DeviceConfigResponse with generated configuration
    """
    device, matching_key, _, _ = await validate_device_access(
        device_id=device_id,
        auth_info=auth_info,
        config_service=config_service,
        audit_service=audit_service,
    )

    try:
        device_dek = await config_service.decrypt_device_dek_with_api_key(
            device, auth_info.api_key, api_key_record=matching_key
        )
        device_private_key = await config_service.decrypt_device_private_key_with_dek(
            device, device_dek
        )
    except ValueError as e:
        await audit_service.log_event(
            network_id=device.network_id,
            actor=auth_info.actor,
            action="ACCESS_DENIED",
            resource_type="device_config",
            resource_id=device_id,
            details={
                "source_ip": auth_info.source_ip,
                "has_api_key": auth_info.api_key is not None,
                "denied_reason": "dek_unwrap_failed",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to decrypt device private key",
        ) from e

    try:
        config_response = await config_service.generate_device_config(
            device=device,
            device_private_key=device_private_key,
            format_type=format_type,
            platform=platform,
            device_dek=device_dek,
        )
    except ValueError as e:
        await audit_service.log_event(
            network_id=device.network_id,
            actor=auth_info.actor,
            action="ACCESS_DENIED",
            resource_type="device_config",
            resource_id=device_id,
            details={
                "source_ip": auth_info.source_ip,
                "has_api_key": auth_info.api_key is not None,
                "denied_reason": "preshared_key_unavailable",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Device configuration unavailable. Contact an administrator.",
        ) from e

    # Log successful configuration retrieval
    await audit_service.log_event(
        network_id=device.network_id,
        actor=auth_info.actor,
        action="RETRIEVE",
        resource_type="device_config",
        resource_id=device_id,
        details={
            "resource_name": device.name,
            "format": format_type,
            "platform": platform,
            "source_ip": auth_info.source_ip,
        },
    )

    return config_response


@router.get("/{device_id}/config", response_model=DeviceConfigResponse)
async def get_device_config(
    device_id: str,
    config_service: Annotated[DeviceConfigService, Depends(get_device_config_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    request: Request,
    format: str = Query(default="wg", description="Configuration format"),
    platform: str | None = Query(
        default=None, description="Mobile platform for optimized config"
    ),
) -> DeviceConfigResponse:
    """Get WireGuard configuration for a specific device.

    This endpoint is used by devices to retrieve their WireGuard configuration.
    Authentication is required via API key and IP allowlist validation.

    Args:
        device_id: ID of the device
        format: Configuration format ('wg', 'json', 'mobile')
        platform: Mobile platform for optimized config
        config_service: Device configuration service
        audit_service: Audit logging service
        request: HTTP request for client information

    Returns:
        Device configuration in requested format

    Raises:
        HTTPException: If device not found or access denied
    """
    auth_info = extract_device_auth_info(request)
    _validate_config_request(format, platform)

    return await _generate_device_config_response(
        device_id=device_id,
        format_type=format,
        platform=platform,
        config_service=config_service,
        audit_service=audit_service,
        auth_info=auth_info,
    )


@router.get("/{device_id}/config/wg", response_class=PlainTextResponse)
async def get_device_config_wg(
    device_id: str,
    config_service: Annotated[DeviceConfigService, Depends(get_device_config_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    request: Request,
) -> PlainTextResponse:
    """Get WireGuard configuration in standard .conf format.

    This is a convenience endpoint that returns the configuration as plain text
    suitable for direct use in WireGuard clients.

    Args:
        device_id: ID of the device
        config_service: Device configuration service
        audit_service: Audit logging service
        request: HTTP request for client information

    Returns:
        Plain text WireGuard configuration file

    Raises:
        HTTPException: If device not found or access denied
    """
    auth_info = extract_device_auth_info(request)

    config_response = await _generate_device_config_response(
        device_id=device_id,
        format_type="wg",
        config_service=config_service,
        audit_service=audit_service,
        auth_info=auth_info,
    )

    return PlainTextResponse(
        content=str(config_response.configuration),
        headers={
            "Content-Disposition": f'attachment; filename="{config_response.device_name.replace(" ", "_")}_wg0.conf"',
            "Content-Type": "text/plain; charset=utf-8",
        },
    )


async def _validate_master_password_access() -> str:
    """Validate master password is unlocked and return it.

    Returns:
        Master password from cache

    Raises:
        HTTPException: If master password not unlocked
    """
    try:
        return get_master_password(require_cache=True)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Master password must be unlocked to access device configurations",
        ) from e


async def _get_device_with_private_key(
    device_id: str,
    config_service: DeviceConfigService,
    master_password: str,
) -> tuple[Any, str]:
    """Get device and decrypt its private key.

    Args:
        device_id: ID of the device
        config_service: Device configuration service
        master_password: Unlocked master password

    Returns:
        Tuple of (device, decrypted_private_key)

    Raises:
        HTTPException: If device not found or decryption fails
    """
    device_service = DeviceService(db=config_service.db)
    try:
        device = await device_service.get_device(device_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    try:
        device_private_key = await config_service.decrypt_device_private_key(
            device, master_password=master_password
        )
        return device, device_private_key
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to decrypt device private key",
        ) from e


async def _generate_admin_config(
    device_id: str,
    config_service: DeviceConfigService,
    audit_service: AuditService,
    request: Request,
    format_type: str = "wg",
    platform: str | None = None,
    access_method: str = "admin_endpoint",
) -> DeviceConfigResponse:
    """Generate device configuration for admin access.

    Args:
        device_id: ID of the device
        config_service: Device configuration service
        audit_service: Audit logging service
        request: HTTP request for client information
        format_type: Configuration format
        platform: Mobile platform for optimized config
        access_method: Method used for access (for audit logging)

    Returns:
        Device configuration in requested format
    """
    master_password = await _validate_master_password_access()
    device, device_private_key = await _get_device_with_private_key(
        device_id, config_service, master_password
    )

    # Decrypt device DEK to use for preshared key decryption
    # This ensures we use the device's cached PSKs which are encrypted with the DEK,
    # rather than falling back to master password which may not work if key rotation
    # didn't re-encrypt network/location PSKs
    device_dek = None
    if device.device_dek_encrypted_master:
        try:
            device_dek = decrypt_device_dek_from_json(
                device.device_dek_encrypted_master, master_password
            )
        except (ValueError, KeyError, TypeError) as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to decrypt device key: {e}",
            ) from e

    config_response = await config_service.generate_device_config(
        device=device,
        device_private_key=device_private_key,
        format_type=format_type,
        platform=platform,
        device_dek=device_dek,
    )

    actor = get_client_actor(request)
    await audit_service.log_event(
        network_id=device.network_id,
        actor=actor,
        action="RETRIEVE",
        resource_type="device_config",
        resource_id=device_id,
        details={
            "resource_name": device.name,
            "format": format_type,
            "platform": platform,
            "accessed_via": access_method,
        },
    )

    return config_response


# Admin endpoints for device config retrieval (require master password unlock)
@router.get("/admin/{device_id}/config", response_model=DeviceConfigResponse)
async def admin_get_device_config(
    device_id: str,
    _: Annotated[None, Depends(require_master_session)],
    config_service: Annotated[DeviceConfigService, Depends(get_device_config_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    request: Request,
    format: str = Query(default="wg", description="Configuration format"),
    platform: str | None = Query(
        default=None, description="Mobile platform for optimized config"
    ),
) -> DeviceConfigResponse:
    """Get WireGuard configuration for a specific device (admin endpoint).

    This endpoint allows administrators to retrieve device configurations.
    Requires the master password to be unlocked.

    Args:
        device_id: ID of the device
        format: Configuration format ('wg', 'json', 'mobile')
        platform: Mobile platform for optimized config
        config_service: Device configuration service
        audit_service: Audit logging service
        request: HTTP request for client information

    Returns:
        Device configuration in requested format

    Raises:
        HTTPException: If device not found or master password not unlocked
    """
    _validate_config_request(format, platform)
    return await _generate_admin_config(
        device_id=device_id,
        config_service=config_service,
        audit_service=audit_service,
        request=request,
        format_type=format,
        platform=platform,
        access_method="admin_endpoint",
    )


@router.get("/admin/{device_id}/config/wg", response_class=PlainTextResponse)
async def admin_get_device_config_wg(
    device_id: str,
    _: Annotated[None, Depends(require_master_session)],
    config_service: Annotated[DeviceConfigService, Depends(get_device_config_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    request: Request,
) -> PlainTextResponse:
    """Get WireGuard configuration in standard .conf format (admin endpoint).

    This is a convenience endpoint that returns the configuration as plain text
    suitable for direct use in WireGuard clients. Requires master password unlock.

    Args:
        device_id: ID of the device
        config_service: Device configuration service
        audit_service: Audit logging service
        request: HTTP request for client information

    Returns:
        Plain text WireGuard configuration file with no-cache headers

    Raises:
        HTTPException: If device not found or master password not unlocked
    """
    config_response = await _generate_admin_config(
        device_id=device_id,
        config_service=config_service,
        audit_service=audit_service,
        request=request,
        format_type="wg",
        access_method="admin_endpoint_wg",
    )

    return PlainTextResponse(
        content=str(config_response.configuration),
        headers={
            "Content-Disposition": f'attachment; filename="{config_response.device_name.replace(" ", "_")}_wg0.conf"',
            "Content-Type": "text/plain; charset=utf-8",
            "Cache-Control": "no-store, no-cache, must-revalidate, private",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("/generate-keys", response_model=WireGuardKeyPairResponse)
async def generate_wireguard_keys(
    method: KeyGenerationMethod,
    _: Annotated[None, Depends(require_master_session)],
) -> WireGuardKeyPairResponse:
    """Generate a new WireGuard key pair using specified method.

    This endpoint generates a new WireGuard key pair using either the
    WireGuard CLI tools (preferred for production) or the Python cryptography
    library (fallback when CLI tools are not available).

    If the CLI method fails, it will automatically fall back to the crypto method.

    Args:
        method: Key generation method ('cli' for WireGuard tools, 'crypto' for Python cryptography)

    Returns:
        WireGuardKeyPairResponse with private and public keys

    Raises:
        HTTPException: If key generation fails
    """
    try:
        # Try CLI method first if requested
        if method.method == "cli":
            try:
                private_key, public_key = key_management.generate_wireguard_keypair_cli()
                return WireGuardKeyPairResponse(
                    private_key=private_key,
                    public_key=public_key,
                    method="cli",
                )
            except RuntimeError:
                # CLI method failed, fall back to crypto method
                private_key, public_key = key_management.generate_wireguard_keypair()
                return WireGuardKeyPairResponse(
                    private_key=private_key,
                    public_key=public_key,
                    method="crypto",
                )

        # Crypto method
        private_key, public_key = key_management.generate_wireguard_keypair()
        return WireGuardKeyPairResponse(
            private_key=private_key,
            public_key=public_key,
            method="crypto",
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Key generation failed: {str(e)}",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error generating keys: {str(e)}",
        ) from e


@router.post(
    "/generate-preshared-key", response_model=WireGuardPresharedKeyResponse
)
async def generate_wireguard_preshared_key_endpoint(
    _: Annotated[None, Depends(require_master_session)]
) -> WireGuardPresharedKeyResponse:
    """Generate a WireGuard preshared key."""
    preshared_key = key_management.generate_wireguard_preshared_key()
    return WireGuardPresharedKeyResponse(preshared_key=preshared_key)


@router.post(
    "/{device_id}/regenerate-api-key", response_model=APIKeyCreateResponse
)
async def regenerate_device_api_key(
    device_id: str,
    service: Annotated[APIKeyService, Depends(get_api_key_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    request: Request,
    _: Annotated[None, Depends(require_master_session)],
) -> APIKeyCreateResponse:
    """Regenerate an API key for a device (rotate existing or create new)."""
    actor = get_client_actor(request)
    session = getattr(request.state, "master_session", None)
    device_service = DeviceService(db=service.db)

    try:
        device = await service._get_device_or_raise(device_id)
        api_keys = await service.get_api_keys_by_device(device_id)

        if api_keys:
            old_api_key = api_keys[0]
            new_key_value, new_key_hash = generate_api_key()
            new_key_fingerprint = compute_api_key_fingerprint(new_key_value)
            new_api_key = await service.rotate_api_key(
                old_api_key.id, new_key_hash, new_key_fingerprint
            )
            await device_service.update_device_dek_for_api_key(
                new_api_key,
                new_key_value,
                session.session_id if session else None,
            )

            await audit_service.log_event(
                network_id=old_api_key.network_id,
                actor=actor,
                action="ROTATE",
                resource_type="api_key",
                resource_id=old_api_key.id,
                details={
                    "resource_name": old_api_key.name,
                    "device_id": old_api_key.device_id,
                    "old_key_id": old_api_key.id,
                    "new_key_id": new_api_key.id,
                },
            )

            return APIKeyCreateResponse(
                api_key=_api_key_to_response(new_api_key),
                key_value=new_key_value,
            )

        key_value, key_hash = generate_api_key()
        key_fingerprint = compute_api_key_fingerprint(key_value)
        api_key = await service.create_api_key(
            APIKeyCreate(
                device_id=device_id,
                network_id=device.network_id,
                name=f"{device.name} API Key",
                allowed_ip_ranges=None,
                enabled=True,
                expires_at=None,
            ),
            key_hash,
            key_fingerprint,
        )
        await device_service.update_device_dek_for_api_key(
            api_key,
            key_value,
            session.session_id if session else None,
        )

        await audit_service.log_event(
            network_id=api_key.network_id,
            actor=actor,
            action="CREATE",
            resource_type="api_key",
            resource_id=api_key.id,
            details={
                "resource_name": api_key.name,
                "device_id": api_key.device_id,
            },
        )

        return APIKeyCreateResponse(
            api_key=_api_key_to_response(api_key),
            key_value=key_value,
        )

    except (APIKeyNotFoundError, DeviceNotFoundError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except ValueError as e:
        if "Master password" in str(e):
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Master password must be unlocked to update device API key access",
            ) from e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.post(
    "/{device_id}/regenerate-keys", response_model=DeviceKeysRegenerateResponse
)
async def regenerate_device_keys(
    device_id: str,
    method: KeyGenerationMethod,
    service: Annotated[DeviceService, Depends(get_device_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    request: Request,
    _: Annotated[None, Depends(require_master_session)],
) -> DeviceKeysRegenerateResponse:
    """Regenerate WireGuard keys for a specific device.

    This endpoint generates a new key pair for an existing device using
    either WireGuard CLI tools or the Python cryptography library.
    The old private key is replaced with the new encrypted key.

    Args:
        device_id: ID of the device to regenerate keys for
        method: Key generation method ('cli' for WireGuard tools, 'crypto' for Python cryptography)
        service: Device service
        audit_service: Audit logging service
        request: HTTP request for client information

    Returns:
        DeviceKeysRegenerateResponse with updated device info

    Raises:
        HTTPException: If device not found, master password not unlocked, or generation fails
    """
    actor = get_client_actor(request)
    session = getattr(request.state, "master_session", None)

    try:
        # Get the device
        device = await service.get_device(device_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    try:
        network = await service._get_network(device.network_id)

        # Generate new keys with fallback mechanism
        if method.method == "cli":
            try:
                private_key, public_key = key_management.generate_wireguard_keypair_cli()
            except RuntimeError:
                # CLI method failed, fall back to crypto method
                private_key, public_key = key_management.generate_wireguard_keypair()
        else:
            private_key, public_key = key_management.generate_wireguard_keypair()

        # Validate the new public key is unique within the network
        await service.validate_public_key_unique(public_key, network.id, device.id)

        # Get master password for key encryption
        master_password_cache = get_master_password_cache(
            session.session_id if session else None
        )
        try:
            master_password = master_password_cache.get_master_password()
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Master password must be unlocked to regenerate device keys.",
            ) from e

        device_dek = None
        if device.device_dek_encrypted_master:
            device_dek = decrypt_device_dek_from_json(
                device.device_dek_encrypted_master, master_password
            )
        else:
            device_dek = generate_device_dek()
            device.device_dek_encrypted_master = encrypt_device_dek_with_master(
                device_dek, master_password
            )
            device.device_dek_encrypted_api_key = None
            if device.api_keys:
                for key_obj in device.api_keys:
                    key_obj.device_dek_encrypted = None

        # Encrypt the new private key
        private_key_encrypted = import_wireguard_private_key_with_dek(
            private_key, device_dek
        )

        # Update device with new keys
        device.public_key = public_key
        device.private_key_encrypted = private_key_encrypted

        await service.db.commit()
        await service.db.refresh(device)

        # Log the key regeneration event
        await audit_service.log_event(
            network_id=device.network_id,
            actor=actor,
            action="UPDATE",
            resource_type="device",
            resource_id=device.id,
            details={
                "resource_name": device.name,
                "public_key_updated": True,
            },
        )

        return DeviceKeysRegenerateResponse(
            id=device.id,
            name=device.name,
            public_key=device.public_key,
            private_key_encrypted=True,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error regenerating keys: {str(e)}",
        ) from e
