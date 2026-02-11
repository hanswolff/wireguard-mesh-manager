"""Router for audit event management endpoints."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.config import settings
from app.database.connection import get_db
from app.database.models import AuditEvent
from app.middleware.auth import require_master_session
from app.routers.utils import get_client_actor
from app.services import audit as audit_service
from app.services import audit_retention
from app.utils.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


router = APIRouter(tags=["audit"])


def _validate_export_format(format: str) -> str:
    """Validate export format."""
    if format not in [
        audit_retention.AuditExportFormat.JSON,
        audit_retention.AuditExportFormat.CSV,
    ]:
        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported format. Supported formats: "
                f"{audit_retention.AuditExportFormat.JSON}, "
                f"{audit_retention.AuditExportFormat.CSV}"
            ),
        )
    return format


def _validate_date_range(
    start_date: datetime | None, end_date: datetime | None
) -> tuple[datetime | None, datetime | None]:
    """Validate and normalize date range."""
    if start_date and start_date.tzinfo is None:
        start_date = start_date.replace(tzinfo=UTC)
    if end_date and end_date.tzinfo is None:
        end_date = end_date.replace(tzinfo=UTC)
    return start_date, end_date


def _build_log_details(
    format: str,
    network_id: str | None,
    start_date: datetime | None,
    end_date: datetime | None,
    actor_filter: str | None,
    action_filter: str | None,
    include_details: bool,
) -> dict[str, Any]:
    """Build standardized log details for audit actions."""
    return {
        "format": format,
        "filters": {
            "network_id": network_id,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "actor": actor_filter,
            "action": action_filter,
            "include_details": include_details,
        },
    }


@router.get("/statistics")
async def get_audit_statistics(
    _: Annotated[None, Depends(require_master_session)],
    db: AsyncSession = Depends(get_db),
    actor: str = Depends(get_client_actor),
) -> dict[str, Any]:
    """Get audit event statistics."""
    export_service = audit_retention.AuditExportService(db)
    stats = await export_service.get_audit_statistics()
    return stats


@router.get("/events")
async def list_audit_events(
    _: Annotated[None, Depends(require_master_session)],
    network_id: str | None = Query(None, description="Filter by network ID"),
    start_date: datetime | None = Query(
        None, description="Filter by start date (ISO format)"
    ),
    end_date: datetime | None = Query(
        None, description="Filter by end date (ISO format)"
    ),
    actor_filter: str | None = Query(
        None, alias="actor", description="Filter by actor name"
    ),
    action_filter: str | None = Query(
        None, alias="action", description="Filter by action type"
    ),
    resource_type_filter: str | None = Query(
        None, alias="resource_type", description="Filter by resource type"
    ),
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(
        50, ge=1, le=1000, description="Number of events per page (max 1000)"
    ),
    include_details: bool = Query(
        False, description="Include event details in response"
    ),
    db: AsyncSession = Depends(get_db),
    client_actor: str = Depends(get_client_actor),
) -> dict[str, Any]:
    """List audit events with pagination and filtering."""
    # Validate date range
    start_date, end_date = _validate_date_range(start_date, end_date)

    # Build base query
    stmt = (
        select(AuditEvent)
        .options(joinedload(AuditEvent.network))
        .order_by(AuditEvent.created_at.desc())
    )

    # Build count query (same filters but without joins and ordering)
    count_stmt = select(func.count(AuditEvent.id))

    # Apply filters to both queries
    filters = []
    if network_id:
        filters.append(AuditEvent.network_id == network_id)

    if start_date:
        filters.append(AuditEvent.created_at >= start_date)

    if end_date:
        filters.append(AuditEvent.created_at <= end_date)

    if actor_filter:
        filters.append(AuditEvent.actor.ilike(f"%{actor_filter}%"))

    if action_filter:
        filters.append(AuditEvent.action == action_filter)

    if resource_type_filter:
        filters.append(AuditEvent.resource_type == resource_type_filter)

    # Apply filters to queries
    for filter_condition in filters:
        stmt = stmt.where(filter_condition)
        count_stmt = count_stmt.where(filter_condition)

    # Get total count
    total_count_result = await db.execute(count_stmt)
    total_count = total_count_result.scalar() or 0

    # Calculate pagination
    offset = (page - 1) * page_size
    total_pages = (total_count + page_size - 1) // page_size

    # Apply pagination to main query
    paginated_stmt = stmt.offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(paginated_stmt)
    events = result.scalars().unique().all()

    # Convert events to dictionary format
    events_data = []
    for event in events:
        event_dict = {
            "id": str(event.id),
            "network_id": str(event.network_id),
            "network_name": event.network.name if event.network else None,
            "actor": event.actor,
            "action": event.action,
            "resource_type": event.resource_type,
            "resource_id": event.resource_id,
            "created_at": event.created_at.isoformat(),
        }

        # Include details if requested and present
        if include_details and event.details:
            try:
                event_dict["details"] = json.loads(event.details)
            except json.JSONDecodeError:
                event_dict["details"] = {"raw": event.details}
        else:
            event_dict["details"] = None

        events_data.append(event_dict)

    return {
        "events": events_data,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1,
        },
        "filters_applied": {
            "network_id": network_id,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "actor": actor_filter,
            "action": action_filter,
            "resource_type": resource_type_filter,
        },
    }


@router.post("/cleanup")
async def cleanup_expired_events(
    _: Annotated[None, Depends(require_master_session)],
    db: AsyncSession = Depends(get_db),
    actor: str = Depends(get_client_actor),
) -> dict[str, Any]:
    """Clean up expired audit events."""
    retention_service = audit_retention.AuditRetentionService(db)
    audit_service_instance = audit_service.AuditService(db)

    # Log the cleanup action
    await audit_service_instance.log_admin_action(
        network_id="system",  # System-level action
        admin_actor=actor,
        action="AUDIT_CLEANUP",
        resource_type="audit_events",
    )

    result = await retention_service.cleanup_expired_events()
    return result


@router.get("/export")
async def export_audit_events(
    _: Annotated[None, Depends(require_master_session)],
    network_id: str | None = Query(None, description="Filter by network ID"),
    start_date: datetime | None = Query(
        None, description="Filter by start date (ISO format)"
    ),
    end_date: datetime | None = Query(
        None, description="Filter by end date (ISO format)"
    ),
    actor_filter: str | None = Query(
        None, alias="actor", description="Filter by actor name"
    ),
    action_filter: str | None = Query(
        None, alias="action", description="Filter by action type"
    ),
    format: str = Query(
        audit_retention.AuditExportFormat.JSON,
        description="Export format (json or csv)",
    ),
    include_details: bool = Query(True, description="Include event details"),
    db: AsyncSession = Depends(get_db),
    client_actor: str = Depends(get_client_actor),
) -> dict[str, Any]:
    """Export audit events with optional filtering."""
    format = _validate_export_format(format)
    start_date, end_date = _validate_date_range(start_date, end_date)

    export_service = audit_retention.AuditExportService(db)
    audit_service_instance = audit_service.AuditService(db)

    await audit_service_instance.log_admin_action(
        network_id=network_id or "system",
        admin_actor=client_actor,
        action="AUDIT_EXPORT",
        resource_type="audit_events",
        changes=_build_log_details(
            format,
            network_id,
            start_date,
            end_date,
            actor_filter,
            action_filter,
            include_details,
        ),
    )

    result = await export_service.export_audit_events(
        network_id=network_id,
        start_date=start_date,
        end_date=end_date,
        actor_filter=actor_filter,
        action_filter=action_filter,
        format_type=format,
        include_details=include_details,
    )

    return result


@router.get("/export/download")
async def download_audit_events(
    _: Annotated[None, Depends(require_master_session)],
    network_id: str | None = Query(None, description="Filter by network ID"),
    start_date: datetime | None = Query(
        None, description="Filter by start date (ISO format)"
    ),
    end_date: datetime | None = Query(
        None, description="Filter by end date (ISO format)"
    ),
    actor_filter: str | None = Query(
        None, alias="actor", description="Filter by actor name"
    ),
    action_filter: str | None = Query(
        None, alias="action", description="Filter by action type"
    ),
    format: str = Query(
        audit_retention.AuditExportFormat.JSON,
        description="Export format (json or csv)",
    ),
    include_details: bool = Query(True, description="Include event details"),
    db: AsyncSession = Depends(get_db),
    client_actor: str = Depends(get_client_actor),
) -> Response:
    """Download audit events as a file."""
    format = _validate_export_format(format)
    start_date, end_date = _validate_date_range(start_date, end_date)

    export_service = audit_retention.AuditExportService(db)
    audit_service_instance = audit_service.AuditService(db)

    await audit_service_instance.log_admin_action(
        network_id=network_id or "system",
        admin_actor=client_actor,
        action="AUDIT_DOWNLOAD",
        resource_type="audit_events",
        changes=_build_log_details(
            format,
            network_id,
            start_date,
            end_date,
            actor_filter,
            action_filter,
            include_details,
        ),
    )

    result = await export_service.export_audit_events(
        network_id=network_id,
        start_date=start_date,
        end_date=end_date,
        actor_filter=actor_filter,
        action_filter=action_filter,
        format_type=format,
        include_details=include_details,
    )

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    filename = f"audit_events_{timestamp}.{format}"

    content_type = (
        "application/json"
        if format == audit_retention.AuditExportFormat.JSON
        else "text/csv"
    )
    content = result["events"]

    return Response(
        content=content if isinstance(content, str) else json.dumps(content, indent=2),
        media_type=content_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@router.get("/retention/info")
async def get_retention_info(
    _: Annotated[None, Depends(require_master_session)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get information about audit retention settings and expired events."""
    retention_service = audit_retention.AuditRetentionService(db)
    cutoff_date = await retention_service.get_expired_events_cutoff()
    expired_count = await retention_service.count_expired_events()

    return {
        "retention_days": settings.audit_retention_days,
        "cutoff_date": cutoff_date.isoformat(),
        "expired_events_count": expired_count,
        "export_batch_size": settings.audit_export_batch_size,
    }
