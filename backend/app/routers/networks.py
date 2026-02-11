"""API routes for WireGuard network management."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.exceptions import ResourceConflictError, ResourceNotFoundError
from app.middleware.auth import require_master_session
from app.routers.network_utils import network_to_response
from app.routers.utils import get_audit_service
from app.routers.utils import get_client_actor
from app.routers.utils import raise_request_validation_error
from app.schemas.networks import (
    WireGuardNetworkCreate,
    WireGuardNetworkResponse,
    WireGuardNetworkUpdate,
)
from app.services.audit import AuditService
from app.services.networks import NetworkService
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["networks"])


def _network_validation_field(message: str) -> str | None:
    message_lower = message.lower()
    if "cidr" in message_lower:
        return "network_cidr"
    if "name" in message_lower:
        return "name"
    if "preshared" in message_lower:
        return "preshared_key"
    return None


def get_network_service(db: Annotated[AsyncSession, Depends(get_db)]) -> NetworkService:
    """Get network service instance."""
    return NetworkService(db)


@router.get("/", response_model=list[WireGuardNetworkResponse])
async def list_networks(
    _: Annotated[None, Depends(require_master_session)],
    service: Annotated[NetworkService, Depends(get_network_service)],
) -> list[WireGuardNetworkResponse]:
    """List all WireGuard networks."""
    networks = await service.list_networks()
    return [network_to_response(network) for network in networks]


@router.get("/{network_id}", response_model=WireGuardNetworkResponse)
async def get_network(
    network_id: str,
    _: Annotated[None, Depends(require_master_session)],
    service: Annotated[NetworkService, Depends(get_network_service)],
) -> WireGuardNetworkResponse:
    """Get a specific WireGuard network by ID."""
    network = await service.get_network(network_id)
    return network_to_response(network)


@router.post(
    "/", response_model=WireGuardNetworkResponse, status_code=status.HTTP_201_CREATED
)
async def create_network(
    network_data: WireGuardNetworkCreate,
    _: Annotated[None, Depends(require_master_session)],
    service: Annotated[NetworkService, Depends(get_network_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    request: Request,
) -> WireGuardNetworkResponse:
    """Create a new WireGuard network."""
    actor = get_client_actor(request)
    session = getattr(request.state, "master_session", None)

    # Log incoming request data for debugging
    logger.info(
        "Creating network",
        extra={
            "action": "CREATE_NETWORK_REQUEST",
            "actor": actor,
            "network_name": network_data.name,
            "network_cidr": network_data.network_cidr,
            "dns_servers": network_data.dns_servers,
            "mtu": network_data.mtu,
            "persistent_keepalive": network_data.persistent_keepalive,
            "has_interface_properties": network_data.interface_properties is not None,
        },
    )

    try:
        network = await service.create_network(
            network_data, session_id=session.session_id if session else None
        )
    except ResourceConflictError as e:
        logger.error(
            "Network creation failed - conflict",
            exc_info=e,
            extra={
                "action": "CREATE_NETWORK_FAILED",
                "actor": actor,
                "network_name": network_data.name,
                "error_type": "conflict",
                "error_message": str(e),
            },
        )
        raise_request_validation_error(str(e), _network_validation_field(str(e)))
    except ResourceNotFoundError as e:
        logger.error(
            "Network creation failed - missing resource",
            exc_info=e,
            extra={
                "action": "CREATE_NETWORK_FAILED",
                "actor": actor,
                "network_name": network_data.name,
                "error_type": "not_found",
                "error_message": str(e),
            },
        )
        raise
    except ValueError as e:
        logger.error(
            "Network creation failed - validation error",
            exc_info=e,
            extra={
                "action": "CREATE_NETWORK_FAILED",
                "actor": actor,
                "network_name": network_data.name,
                "error_type": "validation_error",
                "error_message": str(e),
            },
        )
        raise_request_validation_error(str(e), _network_validation_field(str(e)))
    except Exception as e:
        logger.error(
            "Network creation failed - unexpected error",
            exc_info=e,
            extra={
                "action": "CREATE_NETWORK_FAILED",
                "actor": actor,
                "network_name": network_data.name,
                "error_type": "unexpected_error",
                "error_message": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create network",
        ) from e

    # Log the creation event
    await audit_service.log_event(
        network_id=network.id,
        actor=actor,
        action="CREATE",
        resource_type="network",
        resource_id=network.id,
        details={
            "resource_name": network.name,
            "description": network_data.description,
        },
    )

    logger.info(
        "Network created successfully",
        extra={
            "action": "CREATE_NETWORK_SUCCESS",
            "network_id": network.id,
            "network_name": network.name,
            "actor": actor,
        },
    )

    return network_to_response(network)


@router.put("/{network_id}", response_model=WireGuardNetworkResponse)
async def update_network(
    network_id: str,
    network_data: WireGuardNetworkUpdate,
    _: Annotated[None, Depends(require_master_session)],
    service: Annotated[NetworkService, Depends(get_network_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    request: Request,
) -> WireGuardNetworkResponse:
    """Update a WireGuard network."""
    actor = get_client_actor(request)
    session = getattr(request.state, "master_session", None)

    # Log incoming request data for debugging
    logger.info(
        "Updating network",
        extra={
            "action": "UPDATE_NETWORK_REQUEST",
            "network_id": network_id,
            "actor": actor,
            "update_data": {
                "name": network_data.name,
                "description": network_data.description,
                "network_cidr": network_data.network_cidr,
            },
        },
    )

    # Get old network for audit trail
    old_network = await service.get_network(network_id)

    # Update the network
    try:
        network = await service.update_network(
            network_id,
            network_data,
            session_id=session.session_id if session else None,
        )
    except ResourceConflictError as e:
        logger.error(
            "Network update failed - conflict",
            exc_info=e,
            extra={
                "action": "UPDATE_NETWORK_FAILED",
                "network_id": network_id,
                "actor": actor,
                "error_type": "conflict",
                "error_message": str(e),
            },
        )
        raise_request_validation_error(str(e), _network_validation_field(str(e)))
    except ResourceNotFoundError as e:
        logger.error(
            "Network update failed - missing resource",
            exc_info=e,
            extra={
                "action": "UPDATE_NETWORK_FAILED",
                "network_id": network_id,
                "actor": actor,
                "error_type": "not_found",
                "error_message": str(e),
            },
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except ValueError as e:
        logger.error(
            "Network update failed - validation error",
            exc_info=e,
            extra={
                "action": "UPDATE_NETWORK_FAILED",
                "network_id": network_id,
                "actor": actor,
                "error_type": "validation_error",
                "error_message": str(e),
            },
        )
        raise_request_validation_error(str(e), _network_validation_field(str(e)))
    except Exception as e:
        logger.error(
            "Network update failed - unexpected error",
            exc_info=e,
            extra={
                "action": "UPDATE_NETWORK_FAILED",
                "network_id": network_id,
                "actor": actor,
                "error_type": "unexpected_error",
                "error_message": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update network",
        ) from e

    # Log the update event with changes
    changes = {}
    update_data = network_data.model_dump(exclude_unset=True)
    for key, new_value in update_data.items():
        old_value = getattr(old_network, key, None)
        if old_value != new_value:
            changes[key] = {"old": old_value, "new": new_value}

    if changes:  # Only log if there were actual changes
        await audit_service.log_admin_action(
            network_id=network_id,
            admin_actor=actor,
            action="UPDATE",
            resource_type="network",
            resource_id=network_id,
            resource_name=network.name,
            changes=changes,
        )

    logger.info(
        "Network updated successfully",
        extra={
            "action": "UPDATE_NETWORK_SUCCESS",
            "network_id": network_id,
            "network_name": network.name,
            "actor": actor,
            "changes_count": len(changes),
        },
    )

    return network_to_response(network)


@router.delete("/{network_id}")
async def delete_network(
    network_id: str,
    _: Annotated[None, Depends(require_master_session)],
    service: Annotated[NetworkService, Depends(get_network_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    request: Request,
) -> dict[str, str]:
    """Delete a WireGuard network."""
    actor = get_client_actor(request)
    network = await service.get_network(network_id)

    # Log the deletion event before deleting
    await audit_service.log_event(
        network_id=network_id,
        actor=actor,
        action="DELETE",
        resource_type="network",
        resource_id=network_id,
        details={
            "resource_name": network.name,
            "device_count": len(network.devices) if network.devices else 0,
            "location_count": len(network.locations) if network.locations else 0,
        },
    )

    await service.delete_network(network_id)
    return {"message": f"Network '{network.name}' deleted successfully"}
