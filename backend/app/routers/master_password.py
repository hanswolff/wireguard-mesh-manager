"""Router for master password management operations."""

from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.database.connection import AsyncSession, AsyncSessionLocal, get_db
from app.database.models import Device, WireGuardNetwork
from app.middleware.auth import (
    MasterSessionInfo,
    get_master_session,
    require_master_session,
)
from app.services.master_password import (
    get_master_password_cache,
    session_manager,
)
from app.services.master_session import master_session_manager
from app.utils.key_management import (
    decrypt_device_dek_from_json,
    decrypt_private_key_from_json,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/master-password",
    tags=["master-password"],
)


class MasterPasswordUnlockRequest(BaseModel):
    """Request model for unlocking the master password cache."""

    master_password: str = Field(..., min_length=1, description="Master password to cache")
    ttl_hours: float | None = Field(
        None, description="Custom TTL in hours", ge=0.1, le=24.0
    )
    bootstrap_token: str | None = Field(
        None,
        description=(
            "Bootstrap token required for initial unlock when database is empty. "
            "Not required once bootstrapped (has encrypted data)."
        ),
    )


class MasterPasswordUnlockResponse(BaseModel):
    """Response model for master password unlock operations."""

    success: bool = Field(..., description="Whether unlock was successful")
    message: str = Field(..., description="Status message")
    expires_at: str | None = Field(None, description="When the cache expires")
    password_id: str | None = Field(None, description="ID of the cached password")
    session_token: str | None = Field(
        None, description="Master session token for subsequent requests"
    )


class MasterPasswordStatusResponse(BaseModel):
    """Response model for master password cache status."""

    is_unlocked: bool = Field(..., description="Whether cache is unlocked")
    password_id: str | None = Field(None, description="ID of cached password")
    expires_at: str | None = Field(None, description="When cache expires (absolute)")
    idle_expires_at: str | None = Field(
        None, description="When cache expires (idle timeout)"
    )
    access_count: int = Field(..., description="Number of times password was accessed")
    last_access: str | None = Field(None, description="Last access time")
    ttl_seconds: float = Field(..., description="Time to live in seconds")
    idle_ttl_seconds: float = Field(..., description="Idle time to live in seconds")
    session_id: str | None = Field(None, description="Session ID (if session-based)")


class MasterPasswordExtendTTLRequest(BaseModel):
    """Request model for extending master password cache TTL."""

    additional_hours: float = Field(
        default=1.0,
        description="Additional hours to extend TTL by",
        ge=0.1,
        le=24.0,
    )


class MasterPasswordExtendTTLResponse(BaseModel):
    """Response model for TTL extension operations."""

    success: bool = Field(..., description="Whether TTL was extended")
    message: str = Field(..., description="Status message")
    new_expires_at: str | None = Field(None, description="New expiration time")


class MasterPasswordIsUnlockedResponse(BaseModel):
    """Response model for checking if cache is unlocked (public endpoint)."""

    is_unlocked: bool = Field(..., description="Whether cache is currently unlocked")


@router.get("/is-unlocked", response_model=MasterPasswordIsUnlockedResponse)
async def is_master_password_unlocked(
    http_request: Request,
) -> MasterPasswordIsUnlockedResponse:
    """Check if the master password cache is currently unlocked.

    This is a public endpoint that can be called without authentication.
    It only returns whether the cache is unlocked, without exposing any
    sensitive information about the cache state.

    Returns:
        Unlock status response
    """
    try:
        cache = get_master_password_cache()
        status_info = cache.get_status()
        return MasterPasswordIsUnlockedResponse(is_unlocked=status_info["is_unlocked"])
    except Exception as e:
        logger.error("Failed to check master password unlock status", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check unlock status",
        ) from e


@router.post("/unlock", response_model=MasterPasswordUnlockResponse)
async def unlock_master_password(
    http_request: Request,
    request: MasterPasswordUnlockRequest,
    db: AsyncSession = Depends(get_db),
) -> MasterPasswordUnlockResponse:
    """Unlock the master password cache.

    This endpoint caches the master password in memory for the specified TTL,
    allowing subsequent operations to use the cached password without requiring
    it to be provided in each request.

    If encrypted data exists in the database, the password is validated by
    attempting to decrypt a network's private key. If the database is empty
    (first-time bootstrap), the bootstrap token is required to authorize the
    initial setup.

    A successful unlock returns a master session token for admin access.

    Args:
        http_request: The HTTP request object for authentication
        request: Unlock request containing master password, optional TTL, and bootstrap token
    Returns:
        Unlock response with status and cache information

    Raises:
        HTTPException: If master password is invalid or bootstrap token is missing/invalid
    """
    from app.config import settings

    client_ip = http_request.client.host if http_request.client else None
    user_agent = http_request.headers.get("User-Agent")

    async def log_unlock_failure(reason: str) -> None:
        try:
            from app.services.audit import AuditService

            audit_service = AuditService(db)
            await audit_service.log_event(
                network_id=None,
                actor=f"ip:{client_ip}" if client_ip else "unknown",
                action="UNLOCK_FAILED",
                resource_type="master_password",
                resource_id=None,
                details={
                    "reason": reason,
                    "source_ip": client_ip,
                    "user_agent": user_agent,
                    "bootstrap_provided": request.bootstrap_token is not None,
                    "path": http_request.url.path,
                },
            )
        except Exception:
            # Avoid breaking unlock responses when audit logging fails.
            return

    try:
        # Validate master password by attempting to decrypt existing data
        stmt = select(WireGuardNetwork).limit(1)
        result = await db.execute(stmt)
        network = result.scalar_one_or_none()

        # If a network exists with an encrypted private key, verify the password
        if network and network.private_key_encrypted:
            try:
                decrypt_private_key_from_json(
                    network.private_key_encrypted, request.master_password
                )
            except (ValueError, KeyError, TypeError) as e:
                logger.warning(
                    "Master password validation failed during unlock",
                    extra={"error": str(e)},
                )
                await log_unlock_failure("invalid_master_password")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid master password",
                ) from None
        # For mesh topology, networks don't have keys - validate against a device
        else:
            # Try to find a device to validate the password against
            device_stmt = select(Device).limit(1)
            device_result = await db.execute(device_stmt)
            device = device_result.scalar_one_or_none()

            if device:
                try:
                    if device.device_dek_encrypted_master:
                        decrypt_device_dek_from_json(
                            device.device_dek_encrypted_master,
                            request.master_password,
                        )
                    else:
                        decrypt_private_key_from_json(
                            device.private_key_encrypted, request.master_password
                        )
                except (ValueError, KeyError, TypeError) as e:
                    logger.warning(
                        "Master password validation failed during unlock",
                        extra={"error": str(e)},
                    )
                    await log_unlock_failure("invalid_master_password")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid master password",
                    ) from None
            else:
                # No encrypted data found - this is a bootstrap scenario
                # Require bootstrap token for initial setup authorization
                if not request.bootstrap_token:
                    # Allow password only if bootstrap_token is explicitly set to empty
                    # for backward compatibility with existing configs
                    if settings.bootstrap_token == "":
                        logger.warning(
                            "Bootstrap token explicitly configured as empty - "
                            "allowing password-only unlock for backward compatibility"
                        )
                    else:
                        logger.warning(
                            "Bootstrap attempt without bootstrap_token on empty database"
                        )
                        await log_unlock_failure("bootstrap_token_required")
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail=(
                                "Bootstrap required for initial setup. "
                                "Provide a bootstrap token configured in backend settings."
                            ),
                        )
                # If bootstrap_token is configured, validate it
                if settings.bootstrap_token:
                    if not secrets.compare_digest(
                        request.bootstrap_token, settings.bootstrap_token
                    ):
                        logger.warning("Invalid bootstrap token provided")
                        await log_unlock_failure("invalid_bootstrap_token")
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Invalid bootstrap token",
                        )
                    logger.info(
                        "Bootstrap token validated successfully for initial setup"
                    )

        cache = get_master_password_cache()
        success = cache.unlock(
            master_password=request.master_password,
            ttl_hours=request.ttl_hours,
        )

        if not success:
            logger.warning("Failed to unlock master password cache")
            await log_unlock_failure("master_password_cache_unlock_failed")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to unlock master password cache",
            )

        status_info = cache.get_status()
        session_token, session = master_session_manager.create_session(
            ttl_hours=request.ttl_hours,
            ip_address=client_ip,
            user_agent=user_agent,
        )

        logger.info(
            "Master password cache unlocked via API",
            extra={
                "session_id": session.session_id,
                "password_id": status_info["password_id"],
                "expires_at": status_info["expires_at"],
            },
        )

        return MasterPasswordUnlockResponse(
            success=True,
            message="Master password cache unlocked successfully",
            expires_at=status_info["expires_at"],
            password_id=status_info["password_id"],
            session_token=session_token,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error during master password unlock", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unlock master password cache",
        ) from e


@router.post("/lock")
async def lock_master_password(
    http_request: Request,
    session: MasterSessionInfo | None = Depends(get_master_session),
    _: Annotated[None, Depends(require_master_session)] = None,
) -> MasterPasswordUnlockResponse:
    """Manually lock the master password cache and clear cached data.

    This endpoint immediately locks the cache and securely clears any
    cached master password from memory.

    Requires master session authentication.
    """
    try:
        cache = get_master_password_cache()
        cache.lock()
        if session:
            master_session_manager.remove_session(session.session_id)

        logger.info(
            "Master password cache locked via API",
            extra={"session_id": session.session_id if session else None},
        )

        return MasterPasswordUnlockResponse(
            success=True,
            message="Master password cache locked successfully",
            expires_at=None,
            password_id=None,
        )

    except Exception as e:
        logger.error("Failed to lock master password cache", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to lock master password cache",
        ) from e


@router.get("/status", response_model=MasterPasswordStatusResponse)
async def get_master_password_status(
    http_request: Request,
    session: MasterSessionInfo | None = Depends(get_master_session),
    _: Annotated[None, Depends(require_master_session)] = None,
) -> MasterPasswordStatusResponse:
    """Get the current status of the master password cache.

    This endpoint provides monitoring information about the cache state
    without exposing any sensitive data.

    Requires master session authentication.
    """
    try:
        cache = get_master_password_cache()
        status_info = cache.get_status()

        return MasterPasswordStatusResponse(**status_info)

    except Exception as e:
        logger.error("Failed to get master password cache status", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get cache status",
        ) from e


@router.post("/extend-ttl", response_model=MasterPasswordExtendTTLResponse)
async def extend_master_password_ttl(
    http_request: Request,
    request: MasterPasswordExtendTTLRequest,
    session: MasterSessionInfo | None = Depends(get_master_session),
    _: Annotated[None, Depends(require_master_session)] = None,
) -> MasterPasswordExtendTTLResponse:
    """Extend the TTL of the current master password cache.

    This endpoint extends the time-to-live of the cached master password,
    useful for long-running operations.

    Requires master session authentication.
    """
    try:
        cache = get_master_password_cache()
        success = cache.extend_ttl(additional_hours=request.additional_hours)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot extend TTL: cache is locked or not unlocked",
            )

        if session:
            master_session_manager.extend_session(
                session.session_id, request.additional_hours
            )

        status_info = cache.get_status()

        logger.info(
            "Master password cache TTL extended via API",
            extra={
                "session_id": session.session_id if session else None,
                "password_id": status_info["password_id"],
                "new_expires_at": status_info["expires_at"],
                "additional_hours": request.additional_hours,
            },
        )

        return MasterPasswordExtendTTLResponse(
            success=True,
            message="TTL extended successfully",
            new_expires_at=status_info["expires_at"],
        )

    except ValueError as e:
        logger.warning("Invalid TTL extension request")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error("Failed to extend master password cache TTL", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to extend TTL",
        ) from e


@router.post("/refresh-access")
async def refresh_master_password_access(
    http_request: Request,
    session: MasterSessionInfo | None = Depends(get_master_session),
    _: Annotated[None, Depends(require_master_session)] = None,
) -> dict[str, str]:
    """Refresh the access time of the master password cache.

    This endpoint updates the last access time without incrementing
    the access counter, useful for heartbeat operations.

    Requires master session authentication.

    Args:
        http_request: The HTTP request object for authentication

    Returns:
        Refresh response
    """
    try:
        cache = get_master_password_cache()
        success = cache.refresh_access()

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot refresh access: cache is locked or not unlocked",
            )

        return {"message": "Access time refreshed successfully"}

    except Exception as e:
        logger.error("Failed to refresh master password cache access", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh access",
        ) from e


# Session management endpoints
@router.get("/sessions")
async def get_all_sessions(
    http_request: Request,
    _: Annotated[None, Depends(require_master_session)] = None,
) -> dict[str, list[dict] | int]:
    """Get status of all sessions (for monitoring).

    Requires master session authentication.

    Returns:
        Dictionary with session statuses and count
    """
    try:
        sessions_status = session_manager.get_all_sessions_status()
        session_count = session_manager.get_session_count()

        return {
            "sessions": sessions_status,
            "session_count": session_count,
        }

    except Exception as e:
        logger.error("Failed to get session information", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get session information",
        ) from e


@router.delete("/sessions/{session_id}")
async def remove_session(
    http_request: Request,
    session_id: str,
    _: Annotated[None, Depends(require_master_session)] = None,
) -> dict[str, str]:
    """Remove a specific session and lock its cache.

    Requires master session authentication.

    Args:
        http_request: The HTTP request object for authentication
        session_id: Session ID to remove

    Returns:
        Removal response
    """
    try:
        session_manager.remove_session(session_id)

        return {"message": f"Session {session_id} removed successfully"}

    except Exception as e:
        logger.error(
            "Failed to remove session",
            extra={"session_id": session_id},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove session",
        ) from e


@router.post("/sessions/cleanup")
async def cleanup_expired_sessions(
    http_request: Request,
    _: Annotated[None, Depends(require_master_session)] = None,
) -> dict[str, str | int]:
    """Clean up expired session caches.

    Requires master session authentication.

    Returns:
        Cleanup response with number of sessions removed
    """
    try:
        cleaned_count = session_manager.cleanup_expired_sessions()

        return {
            "cleaned_sessions": cleaned_count,
            "message": f"Cleaned up {cleaned_count} expired sessions",
        }

    except Exception as e:
        logger.error("Failed to cleanup expired sessions", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup expired sessions",
        ) from e
