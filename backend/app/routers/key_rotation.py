"""API routes for master password rotation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.database.connection import get_db
from app.middleware.auth import require_master_session
from app.routers.utils import get_audit_service, get_client_actor
from app.schemas.key_rotation import (
    KeyRotationStatus,
    MasterPasswordRotate,
    PasswordValidationResponse,
)
from app.services.key_rotation import KeyRotationService
from app.utils.password_policy import PasswordPolicy

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from app.services.audit import AuditService

router = APIRouter(prefix="/key-rotation", tags=["key-rotation"])


def get_key_rotation_service(db: AsyncSession = Depends(get_db)) -> KeyRotationService:
    """Get key rotation service instance."""
    return KeyRotationService(db)


@router.post("/rotate", response_model=KeyRotationStatus)
async def rotate_master_password(
    rotate_data: MasterPasswordRotate,
    _: None = Depends(require_master_session),
    service: KeyRotationService = Depends(get_key_rotation_service),
    audit_service: AuditService = Depends(get_audit_service),
    actor: str = Depends(get_client_actor),
) -> KeyRotationStatus:
    """Rotate the master password and re-encrypt stored keys.

    This endpoint:
    1. Validates the current master password
    2. Re-encrypts each device DEK with the new password
    3. Also rotates any preshared keys on devices

    Args:
        rotate_data: Password rotation data
        service: Key rotation service
        audit_service: Audit service for logging
        actor: Client actor information

    Returns:
        KeyRotationStatus with rotation results

    Raises:
        HTTPException: If rotation fails
    """
    # Validate new passwords match
    if rotate_data.new_password != rotate_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="New passwords do not match"
        )

    try:
        # Perform the rotation
        result = await service.rotate_master_password(
            rotate_data.current_password, rotate_data.new_password
        )

        # Check if there were any failures
        if result.failed_networks > 0 or result.failed_devices > 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "message": "Key rotation completed with some failures",
                    "status": result.dict(),
                },
            )

        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from None
    except (KeyError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Key processing error during rotation",
        ) from None
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during key rotation",
        ) from None


@router.get("/estimate")
async def get_rotation_estimate(
    _: None = Depends(require_master_session),
    service: KeyRotationService = Depends(get_key_rotation_service),
) -> dict[str, Any]:
    """Get an estimate of items that will be affected by key rotation.

    Returns:
        Dict with counts of networks, devices, and total keys
    """
    return await service.get_rotation_estimate()


@router.post("/validate-current-password")
async def validate_current_password(
    password_data: dict[str, str],
    _: None = Depends(require_master_session),
    service: KeyRotationService = Depends(get_key_rotation_service),
) -> dict[str, bool]:
    """Validate if the provided current password is correct.

    This endpoint can be used to validate the current password before
    attempting a full rotation operation.

    Args:
        password_data: Dict containing current_password
        service: Key rotation service

    Returns:
        Dict with validation result
    """
    current_password = password_data.get("current_password", "")
    is_valid = await service.validate_current_password(current_password)
    return {"valid": is_valid}


@router.post("/validate-password", response_model=PasswordValidationResponse)
async def validate_password(
    password_data: dict[str, str],
    _: None = Depends(require_master_session),
) -> PasswordValidationResponse:
    """Validate password strength and policy compliance.

    This endpoint validates a password against the security policy
    and provides strength feedback.

    Args:
        password_data: Dict containing password to validate

    Returns:
        PasswordValidationResponse with validation results
    """
    password = password_data.get("password", "")
    result = PasswordPolicy.validate_password(password)
    return PasswordValidationResponse(**result)


@router.get("/password-policy")
async def get_password_policy(
    _: None = Depends(require_master_session),
) -> dict[str, Any]:
    """Get the current password policy requirements.

    Returns:
        Dict with password policy information for UI display
    """
    return {
        "requirements": PasswordPolicy.get_password_requirements(),
        "min_length": PasswordPolicy.MIN_LENGTH,
        "max_length": PasswordPolicy.MAX_LENGTH,
    }
