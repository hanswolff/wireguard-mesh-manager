"""Router for export and import operations."""

from __future__ import annotations

import json
import zipfile
from io import BytesIO
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.exceptions import BusinessRuleViolationError
from app.middleware.auth import require_master_session
from app.schemas.export import ExportConfigsRequest, ExportData, ExportRequest
from app.services.export import ExportImportService
from app.routers.utils import get_client_actor

router = APIRouter(tags=["export"])


@router.get("/networks", response_model=ExportData)
async def export_networks(
    _: Annotated[None, Depends(require_master_session)],
    db: Annotated[AsyncSession, Depends(get_db)],
    exported_by: Annotated[str, Query()] = "system",
    description: str | None = None,
) -> ExportData:
    """Export all networks with their locations and devices.

    Args:
        exported_by: Who is performing the export
        description: Optional description for the export
        db: Database session

    Returns:
        ExportData containing all networks, locations, and devices
    """
    service = ExportImportService(db)
    return await service.export_networks(
        exported_by,
        description,
        network_ids=None,
        include_encrypted_keys=True,
    )


@router.post("", response_model=ExportData)
async def export_networks_from_request(
    export_request: ExportRequest,
    _: Annotated[None, Depends(require_master_session)],
    db: Annotated[AsyncSession, Depends(get_db)],
    request: Request,
) -> ExportData:
    """Export networks from a request body."""
    if export_request.include_api_keys:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API key export is not supported",
        )

    if export_request.format != "json":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use /export/download for ZIP exports",
        )

    service = ExportImportService(db)
    exported_by = get_client_actor(request)
    return await service.export_networks(
        exported_by,
        description=None,
        network_ids=export_request.network_ids,
        include_encrypted_keys=export_request.include_configs,
    )


@router.post("/download")
async def download_export(
    export_request: ExportRequest,
    _: Annotated[None, Depends(require_master_session)],
    db: Annotated[AsyncSession, Depends(get_db)],
    request: Request,
) -> StreamingResponse:
    """Download export data as a ZIP file."""
    if export_request.include_api_keys:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API key export is not supported",
        )

    if export_request.format != "zip":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Export format must be 'zip' for downloads",
        )

    service = ExportImportService(db)
    exported_by = get_client_actor(request)
    export_data = await service.export_networks(
        exported_by,
        description=None,
        network_ids=export_request.network_ids,
        include_encrypted_keys=export_request.include_configs,
    )

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr(
            "networks-export.json", export_data.model_dump_json(indent=2)
        )
    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="networks-export.zip"'
        },
    )


@router.post("/networks")
async def import_networks(
    _: Annotated[None, Depends(require_master_session)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile,
    imported_by: Annotated[str, Query()] = "system",
    overwrite_existing: bool = False,
) -> dict[str, Any]:
    """Import networks from a JSON export file."""
    _validate_json_file(file.filename)
    export_data = await _parse_and_validate_export_file(file)

    try:
        service = ExportImportService(db)
        results = await service.import_networks(
            export_data=export_data,
            imported_by=imported_by,
            overwrite_existing=overwrite_existing,
        )
        return JSONResponse(
            content=results,
            status_code=_determine_response_status(results),
        )
    except BusinessRuleViolationError as e:
        return JSONResponse(
            content={
                "networks_created": 0,
                "networks_updated": 0,
                "locations_created": 0,
                "devices_created": 0,
                "errors": [e.message],
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


def _validate_json_file(filename: str | None) -> None:
    """Validate that the file is a JSON file."""
    if not filename or not filename.endswith(".json"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JSON files are supported for import",
        )


async def _parse_and_validate_export_file(file: UploadFile) -> ExportData:
    """Parse and validate the export file content."""
    try:
        content = await file.read()
        import_data = json.loads(content.decode("utf-8"))
        return ExportData.model_validate(import_data)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON file: {str(e)}",
        ) from None
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid export format: {str(e)}",
        ) from None


def _determine_response_status(results: dict[str, Any]) -> int:
    """Determine the appropriate HTTP status code based on import results."""
    if not results["errors"]:
        return status.HTTP_200_OK

    if any("already exists" in error for error in results["errors"]):
        return status.HTTP_409_CONFLICT

    return status.HTTP_200_OK


@router.post("/networks/{network_id}/configs")
async def export_network_configs(
    network_id: str,
    export_request: ExportConfigsRequest,
    _: Annotated[None, Depends(require_master_session)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StreamingResponse:
    """Export all device configurations for a network as a ZIP file.

    Args:
        network_id: ID of the network to export
        db: Database session
        format: Configuration format ('wg', 'json', 'mobile')
        platform: Mobile platform for optimized config
        include_preshared_keys: Whether to include preshared keys

    Returns:
        StreamingResponse with ZIP file containing all configurations

    Raises:
        HTTPException: If network not found or export fails
    """
    service = ExportImportService(db)

    try:
        # Validate format parameter
        if export_request.format not in ["wg", "json", "mobile"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid format. Must be one of: wg, json, mobile",
            )
        if export_request.format == "mobile" and not export_request.platform:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mobile configuration exports require a platform value",
            )

        # Generate ZIP file
        zip_buffer = await service.export_network_configs(
            network_id=network_id,
            format_type=export_request.format,
            include_preshared_keys=export_request.include_preshared_keys,
            platform=export_request.platform,
        )

        # Get network name for filename
        from sqlalchemy import select

        from app.database.models import WireGuardNetwork

        result = await db.execute(
            select(WireGuardNetwork.name).where(WireGuardNetwork.id == network_id)
        )
        network = result.scalar_one_or_none()
        network_name = network.name if network else "unknown_network"

        # Return ZIP file as streaming response
        filename = f"{network_name}_configs_{export_request.format}.zip".replace(" ", "_")

        return StreamingResponse(
            iter([zip_buffer.getvalue()]),
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )

    except ValueError as e:
        if "Master password cache" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e),
            ) from e
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}",
        ) from e


@router.get("/networks/schema")
async def get_export_schema(
    _: Annotated[None, Depends(require_master_session)],
) -> JSONResponse:
    """Get the JSON schema for export files."""
    schema = ExportData.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    return JSONResponse(
        content=json.loads(json.dumps(schema, sort_keys=True)),
        headers={"Cache-Control": "public, max-age=3600"},
    )
