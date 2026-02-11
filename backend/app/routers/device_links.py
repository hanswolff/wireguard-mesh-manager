"""API routes for device peer link properties."""

from __future__ import annotations

from typing import Annotated

import sqlalchemy.ext.asyncio  # noqa: TC002
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.database.connection import get_db
from app.middleware.auth import require_master_session
from app.schemas.device_links import DevicePeerLinkCreate, DevicePeerLinkResponse
from app.services.device_links import DevicePeerLinkService

AsyncSession: type = sqlalchemy.ext.asyncio.AsyncSession

router = APIRouter(tags=["device-links"])


def get_device_link_service(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> DevicePeerLinkService:
    """Get device peer link service instance."""
    return DevicePeerLinkService(db)


def _link_to_response(link: object) -> DevicePeerLinkResponse:
    """Convert model to response schema."""
    return DevicePeerLinkResponse(
        id=link.id,
        network_id=link.network_id,
        from_device_id=link.from_device_id,
        to_device_id=link.to_device_id,
        properties=link.properties,
        created_at=link.created_at,
        updated_at=link.updated_at,
    )


@router.get(
    "/networks/{network_id}/device-links",
    response_model=list[DevicePeerLinkResponse],
)
async def list_device_links(
    network_id: str,
    _: Annotated[None, Depends(require_master_session)],
    service: Annotated[DevicePeerLinkService, Depends(get_device_link_service)],
) -> list[DevicePeerLinkResponse]:
    """List device peer link properties for a network."""
    links = await service.list_links(network_id)
    return [_link_to_response(link) for link in links]


@router.post(
    "/networks/{network_id}/device-links",
    response_model=DevicePeerLinkResponse,
)
async def upsert_device_link(
    network_id: str,
    payload: DevicePeerLinkCreate,
    _: Annotated[None, Depends(require_master_session)],
    service: Annotated[DevicePeerLinkService, Depends(get_device_link_service)],
    request: Request,
) -> DevicePeerLinkResponse:
    """Create or update a directional device peer link."""
    preshared_key_set = "preshared_key" in payload.model_fields_set
    if not payload.properties and not preshared_key_set:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Properties or preshared_key are required. Use DELETE to clear a link.",
        )
    try:
        session = getattr(request.state, "master_session", None)
        link = await service.upsert_link(
            network_id,
            from_device_id=payload.from_device_id,
            to_device_id=payload.to_device_id,
            properties=payload.properties,
            preshared_key=payload.preshared_key,
            preshared_key_set=preshared_key_set,
            session_id=session.session_id if session else None,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return _link_to_response(link)


@router.delete(
    "/networks/{network_id}/device-links/{from_device_id}/{to_device_id}",
    response_model=dict,
)
async def delete_device_link(
    network_id: str,
    from_device_id: str,
    to_device_id: str,
    _: Annotated[None, Depends(require_master_session)],
    service: Annotated[DevicePeerLinkService, Depends(get_device_link_service)],
) -> dict[str, str]:
    """Delete a device peer link."""
    deleted = await service.delete_link(network_id, from_device_id, to_device_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Device link not found"
        )
    return {"message": "Device link deleted"}
