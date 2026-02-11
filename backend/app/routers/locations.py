"""API routes for location management."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.middleware.auth import require_master_session
from app.routers.utils import get_audit_service
from app.routers.utils import get_client_actor
from app.routers.utils import raise_request_validation_error
from app.exceptions import ResourceConflictError
from app.schemas.locations import LocationCreate, LocationResponse, LocationUpdate
from app.services.audit import AuditService
from app.services.locations import LocationService

router = APIRouter(tags=["locations"])


def get_location_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LocationService:
    """Get location service instance."""
    return LocationService(db)


def _location_to_response(location: Any) -> LocationResponse:
    """Convert location model to response with counts and network name."""
    return LocationResponse(
        id=location.id,
        network_id=location.network_id,
        name=location.name,
        description=location.description,
        external_endpoint=location.external_endpoint,
        internal_endpoint=location.internal_endpoint,
        interface_properties=location.interface_properties,
        created_at=location.created_at,
        updated_at=location.updated_at,
        network_name=location.network.name if location.network else None,
        device_count=len(location.devices) if location.devices else 0,
    )


def _location_validation_field(message: str) -> str | None:
    message_lower = message.lower()
    if "name" in message_lower:
        return "name"
    if "external endpoint" in message_lower:
        return "external_endpoint"
    if "internal endpoint" in message_lower:
        return "internal_endpoint"
    if "preshared" in message_lower:
        return "preshared_key"
    return None


@router.get("/", response_model=list[LocationResponse])
async def list_locations(
    _: Annotated[None, Depends(require_master_session)],
    service: Annotated[LocationService, Depends(get_location_service)],
    network_id: Annotated[str | None, Query(description="Filter by network ID")] = None,
) -> list[LocationResponse]:
    """List all locations, optionally filtered by network ID."""
    if network_id:
        locations = await service.get_locations_by_network(network_id)
    else:
        locations = await service.list_locations()
    return [_location_to_response(location) for location in locations]


@router.get("/{location_id}", response_model=LocationResponse)
async def get_location(
    location_id: str,
    _: Annotated[None, Depends(require_master_session)],
    service: Annotated[LocationService, Depends(get_location_service)],
) -> LocationResponse:
    """Get a specific location by ID."""
    location = await service.get_location(location_id)
    return _location_to_response(location)


@router.post("/", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
async def create_location(
    location_data: LocationCreate,
    _: Annotated[None, Depends(require_master_session)],
    service: Annotated[LocationService, Depends(get_location_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    request: Request,
) -> LocationResponse:
    """Create a new location."""
    actor = get_client_actor(request)
    session = getattr(request.state, "master_session", None)
    try:
        location = await service.create_location(
            location_data, session_id=session.session_id if session else None
        )
    except ResourceConflictError as e:
        raise_request_validation_error(str(e), "name")
    except ValueError as e:
        raise_request_validation_error(str(e), _location_validation_field(str(e)))

    location = await service.get_location(location.id)

    # Log the creation event
    await audit_service.log_event(
        network_id=location.network_id,
        actor=actor,
        action="CREATE",
        resource_type="location",
        resource_id=location.id,
        details={
            "resource_name": location.name,
            "network_id": location.network_id,
            "external_endpoint": location_data.external_endpoint,
            "internal_endpoint": location_data.internal_endpoint,
            "description": location_data.description,
        },
    )

    return _location_to_response(location)


@router.put("/{location_id}", response_model=LocationResponse)
async def update_location(
    location_id: str,
    location_data: LocationUpdate,
    _: Annotated[None, Depends(require_master_session)],
    service: Annotated[LocationService, Depends(get_location_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    request: Request,
) -> LocationResponse:
    """Update a location."""
    actor = get_client_actor(request)
    session = getattr(request.state, "master_session", None)

    # Get old location for audit trail
    old_location = await service.get_location(location_id)

    # Update the location
    try:
        location = await service.update_location(
            location_id,
            location_data,
            session_id=session.session_id if session else None,
        )
    except ResourceConflictError as e:
        raise_request_validation_error(str(e), "name")
    except ValueError as e:
        raise_request_validation_error(str(e), _location_validation_field(str(e)))
    location = await service.get_location(location.id)

    # Log the update event with changes
    changes = {}
    update_data = location_data.model_dump(exclude_unset=True)
    for key, new_value in update_data.items():
        old_value = getattr(old_location, key, None)
        if old_value != new_value:
            changes[key] = {"old": old_value, "new": new_value}

    if changes:  # Only log if there were actual changes
        await audit_service.log_admin_action(
            network_id=location.network_id,
            admin_actor=actor,
            action="UPDATE",
            resource_type="location",
            resource_id=location_id,
            resource_name=location.name,
            changes=changes,
        )

    return _location_to_response(location)


@router.delete("/{location_id}")
async def delete_location(
    location_id: str,
    _: Annotated[None, Depends(require_master_session)],
    service: Annotated[LocationService, Depends(get_location_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    request: Request,
) -> dict[str, str]:
    """Delete a location."""
    actor = get_client_actor(request)
    location = await service.get_location(location_id)

    # Log the deletion event before deleting
    await audit_service.log_event(
        network_id=location.network_id,
        actor=actor,
        action="DELETE",
        resource_type="location",
        resource_id=location_id,
        details={
            "resource_name": location.name,
            "device_count": len(location.devices) if location.devices else 0,
        },
    )

    await service.delete_location(location_id)
    return {"message": f"Location '{location.name}' deleted successfully"}
