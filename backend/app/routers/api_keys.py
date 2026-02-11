"""API routes for API key management."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, status

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.services.audit import AuditService
from app.middleware.auth import (
    MasterSessionInfo,
    get_master_session,
    require_master_session,
)
from app.routers.utils import get_audit_service
from app.schemas.devices import (
    APIKeyCreate,
    APIKeyCreateResponse,
    APIKeyResponse,
    APIKeyRotateResponse,
    APIKeyUpdate,
)
from app.services.api_key import APIKeyService
from app.services.devices import DeviceService
from app.utils.api_key import (
    APIKeyNotFoundError,
    DeviceNotFoundError,
    compute_api_key_fingerprint,
    generate_api_key,
)

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


def get_api_key_service(db: AsyncSession = Depends(get_db)) -> APIKeyService:
    """Get API key service instance."""
    return APIKeyService(db)


def _api_key_to_response(api_key) -> APIKeyResponse:
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


async def _sync_device_dek_for_api_key(
    *,
    api_key,
    key_value: str,
    service: APIKeyService,
    audit_service: AuditService,
    actor: str,
    session: MasterSessionInfo | None,
) -> None:
    """Ensure device DEK is encrypted for the provided API key."""
    device_service = DeviceService(service.db)
    session_id = session.session_id if session else None

    # Extract values from api_key object before async operations to avoid lazy loading issues
    api_key_id = api_key.id
    device_id = api_key.device_id
    network_id = api_key.network_id
    api_key_name = api_key.name

    try:
        await device_service.update_device_dek_for_api_key(
            api_key, key_value, session_id
        )
        await audit_service.log_event(
            network_id=network_id,
            actor=actor,
            action="UPDATE",
            resource_type="device_dek",
            resource_id=device_id,
            details={
                "status": "success",
                "api_key_id": api_key_id,
                "device_id": device_id,
                "operation": "rewrap",
            },
        )
    except ValueError as exc:
        await audit_service.log_event(
            network_id=network_id,
            actor=actor,
            action="UPDATE",
            resource_type="device_dek",
            resource_id=device_id,
            details={
                "status": "failure",
                "api_key_id": api_key_id,
                "device_id": device_id,
                "operation": "rewrap",
                "error": str(exc),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Master password must be unlocked to update device API key access",
        ) from exc
    except Exception as exc:
        await audit_service.log_event(
            network_id=network_id,
            actor=actor,
            action="UPDATE",
            resource_type="device_dek",
            resource_id=device_id,
            details={
                "status": "failure",
                "api_key_id": api_key_id,
                "device_id": device_id,
                "operation": "rewrap",
                "error": str(exc),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update device API key access",
        ) from exc


@router.get("/", response_model=list[APIKeyResponse])
async def list_api_keys(
    service: APIKeyService = Depends(get_api_key_service),
    _: None = Depends(require_master_session),
    device_id: str | None = None,
) -> list[APIKeyResponse]:
    """List API keys, optionally filtered by device ID."""
    api_keys = await service.list_api_keys(device_id=device_id)
    return [_api_key_to_response(api_key) for api_key in api_keys]


@router.get("/device/{device_id}", response_model=list[APIKeyResponse])
async def get_api_keys_by_device(
    device_id: str,
    service: APIKeyService = Depends(get_api_key_service),
    _: None = Depends(require_master_session),
) -> list[APIKeyResponse]:
    """Get all API keys for a specific device."""
    try:
        api_keys = await service.get_api_keys_by_device(device_id)
        return [_api_key_to_response(api_key) for api_key in api_keys]
    except (APIKeyNotFoundError, DeviceNotFoundError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get("/{api_key_id}", response_model=APIKeyResponse)
async def get_api_key(
    api_key_id: str,
    service: APIKeyService = Depends(get_api_key_service),
    _: None = Depends(require_master_session),
) -> APIKeyResponse:
    """Get a specific API key by ID."""
    try:
        api_key = await service.get_api_key(api_key_id)
        return _api_key_to_response(api_key)
    except (APIKeyNotFoundError, DeviceNotFoundError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post(
    "/", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED
)
async def create_api_key(
    api_key_data: APIKeyCreate,
    service: APIKeyService = Depends(get_api_key_service),
    audit_service: AuditService = Depends(get_audit_service),
    session: MasterSessionInfo | None = Depends(get_master_session),
    _: None = Depends(require_master_session),
) -> APIKeyCreateResponse:
    """Create a new API key for a device."""
    actor = session.actor if session else "master-session:unknown"

    try:
        key_value, key_hash = generate_api_key()
        key_fingerprint = compute_api_key_fingerprint(key_value)
        api_key = await service.create_api_key(
            api_key_data, key_hash, key_fingerprint
        )
        await _sync_device_dek_for_api_key(
            api_key=api_key,
            key_value=key_value,
            service=service,
            audit_service=audit_service,
            actor=actor,
            session=session,
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
                "allowed_ip_ranges": api_key.allowed_ip_ranges,
                "expires_at": (
                    api_key.expires_at.isoformat() if api_key.expires_at else None
                ),
            },
        )

        return APIKeyCreateResponse(
            api_key=_api_key_to_response(api_key),
            key_value=key_value,
        )

    except (APIKeyNotFoundError, DeviceNotFoundError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.put("/{api_key_id}", response_model=APIKeyResponse)
async def update_api_key(
    api_key_id: str,
    api_key_data: APIKeyUpdate,
    service: APIKeyService = Depends(get_api_key_service),
    audit_service: AuditService = Depends(get_audit_service),
    session: MasterSessionInfo | None = Depends(get_master_session),
    _: None = Depends(require_master_session),
) -> APIKeyResponse:
    """Update an API key."""
    actor = session.actor if session else "master-session:unknown"

    try:
        old_api_key = await service.get_api_key(api_key_id)
        api_key = await service.update_api_key(api_key_id, api_key_data)

        changes = {}
        update_data = api_key_data.model_dump(exclude_unset=True)
        for key, new_value in update_data.items():
            old_value = getattr(old_api_key, key, None)
            if old_value != new_value:
                changes[key] = {"old": old_value, "new": new_value}

        if changes:
            await audit_service.log_event(
                network_id=api_key.network_id,
                actor=actor,
                action="UPDATE",
                resource_type="api_key",
                resource_id=api_key_id,
                details={
                    "resource_name": api_key.name,
                    "changes": changes,
                    "device_id": api_key.device_id,
                },
            )

        return _api_key_to_response(api_key)

    except (APIKeyNotFoundError, DeviceNotFoundError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.post("/{api_key_id}/rotate", response_model=APIKeyRotateResponse)
async def rotate_api_key(
    api_key_id: str,
    service: APIKeyService = Depends(get_api_key_service),
    audit_service: AuditService = Depends(get_audit_service),
    session: MasterSessionInfo | None = Depends(get_master_session),
    _: None = Depends(require_master_session),
) -> APIKeyRotateResponse:
    """Rotate an API key, creating a new key and invalidating the old one."""
    actor = session.actor if session else "master-session:unknown"

    try:
        old_api_key = await service.get_api_key(api_key_id)
        new_key_value, new_key_hash = generate_api_key()
        new_key_fingerprint = compute_api_key_fingerprint(new_key_value)
        new_api_key = await service.rotate_api_key(
            api_key_id, new_key_hash, new_key_fingerprint
        )
        await _sync_device_dek_for_api_key(
            api_key=new_api_key,
            key_value=new_key_value,
            service=service,
            audit_service=audit_service,
            actor=actor,
            session=session,
        )

        await audit_service.log_event(
            network_id=old_api_key.network_id,
            actor=actor,
            action="ROTATE",
            resource_type="api_key",
            resource_id=api_key_id,
            details={
                "resource_name": old_api_key.name,
                "device_id": old_api_key.device_id,
                "old_key_id": old_api_key.id,
                "new_key_id": new_api_key.id,
            },
        )

        return APIKeyRotateResponse(
            old_key=_api_key_to_response(old_api_key),
            new_key=APIKeyCreateResponse(
                api_key=_api_key_to_response(new_api_key),
                key_value=new_key_value,
            ),
        )

    except (APIKeyNotFoundError, DeviceNotFoundError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.post("/device/{device_id}/regenerate", response_model=APIKeyCreateResponse)
async def regenerate_device_api_key(
    device_id: str,
    service: APIKeyService = Depends(get_api_key_service),
    audit_service: AuditService = Depends(get_audit_service),
    session: MasterSessionInfo | None = Depends(get_master_session),
    _: None = Depends(require_master_session),
) -> APIKeyCreateResponse:
    """Regenerate an API key for a device (rotate existing or create new)."""
    actor = session.actor if session else "master-session:unknown"

    try:
        # Check if device exists and get its details
        device = await service._get_device_or_raise(device_id)

        # Check for existing API keys for this device
        api_keys = await service.get_api_keys_by_device(device_id)

        if api_keys:
            # Rotate existing API key
            old_api_key = api_keys[0]
            new_key_value, new_key_hash = generate_api_key()
            new_key_fingerprint = compute_api_key_fingerprint(new_key_value)
            new_api_key = await service.rotate_api_key(
                old_api_key.id, new_key_hash, new_key_fingerprint
            )
            await _sync_device_dek_for_api_key(
                api_key=new_api_key,
                key_value=new_key_value,
                service=service,
                audit_service=audit_service,
                actor=actor,
                session=session,
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
        else:
            # Create new API key
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
            await _sync_device_dek_for_api_key(
                api_key=api_key,
                key_value=key_value,
                service=service,
                audit_service=audit_service,
                actor=actor,
                session=session,
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.post("/{api_key_id}/revoke")
async def revoke_api_key(
    api_key_id: str,
    service: APIKeyService = Depends(get_api_key_service),
    audit_service: AuditService = Depends(get_audit_service),
    session: MasterSessionInfo | None = Depends(get_master_session),
    _: None = Depends(require_master_session),
) -> dict[str, str]:
    """Revoke (disable) an API key."""
    actor = session.actor if session else "master-session:unknown"

    try:
        api_key = await service.get_api_key(api_key_id)

        await audit_service.log_event(
            network_id=api_key.network_id,
            actor=actor,
            action="REVOKE",
            resource_type="api_key",
            resource_id=api_key_id,
            details={
                "resource_name": api_key.name,
                "device_id": api_key.device_id,
            },
        )

        revoked_key = await service.revoke_api_key(api_key_id)
        return {"message": f"API key '{revoked_key.name}' revoked successfully"}

    except (APIKeyNotFoundError, DeviceNotFoundError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.delete("/{api_key_id}")
async def delete_api_key(
    api_key_id: str,
    service: APIKeyService = Depends(get_api_key_service),
    audit_service: AuditService = Depends(get_audit_service),
    session: MasterSessionInfo | None = Depends(get_master_session),
    _: None = Depends(require_master_session),
) -> dict[str, str]:
    """Delete an API key permanently."""
    actor = session.actor if session else "master-session:unknown"

    try:
        api_key = await service.get_api_key(api_key_id)

        await audit_service.log_event(
            network_id=api_key.network_id,
            actor=actor,
            action="DELETE",
            resource_type="api_key",
            resource_id=api_key_id,
            details={
                "resource_name": api_key.name,
                "device_id": api_key.device_id,
            },
        )

        await service.delete_api_key(api_key_id)
        return {"message": f"API key '{api_key.name}' deleted successfully"}

    except (APIKeyNotFoundError, DeviceNotFoundError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
