"""Router for backup and restore operations."""

from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.exceptions import BusinessRuleViolationError
from app.middleware.auth import require_master_session
from app.schemas.backup import (
    BackupCreateResponse,
    BackupInfoResponse,
    BackupRestoreRequest,
    BackupRestoreResponse,
)
from app.services.backup import BackupService
from app.services.export import ExportImportService
from app.utils.encryption import decrypt_data, encrypt_data

router = APIRouter(tags=["backup"])


@router.post("/create", response_model=BackupCreateResponse)
async def create_backup(
    _: Annotated[None, Depends(require_master_session)],
    db: Annotated[AsyncSession, Depends(get_db)],
    password: Annotated[str | None, str] = "",
    description: str | None = None,
    exported_by: Annotated[str, str] = "api",
    encrypt: Annotated[bool, bool] = True,
) -> BackupCreateResponse:
    """Create a backup of all networks, locations, and devices.

    Args:
        password: Optional password for encryption. If empty and encrypt=True, a random password is generated.
        description: Optional description for the backup
        exported_by: Who is creating the backup
        encrypt: Whether to encrypt the backup
        db: Database session

    Returns:
        BackupCreateResponse with backup data and optional password
    """
    service = BackupService(db)

    try:
        export_data = await service.export_networks(
            exported_by,
            description,
            network_ids=None,
            include_encrypted_keys=True,
        )

        backup_data = export_data.model_dump()

        if encrypt:
            # Generate password if not provided
            if not password:
                password = service.generate_password()

            encrypted_content = encrypt_data(json.dumps(backup_data), password)
            final_data = encrypted_content
        else:
            final_data = backup_data
            password = None

        # Create backup record
        backup = await service.create_backup_record(
            description=description,
            exported_by=exported_by,
            encrypted=encrypt,
            data=final_data,
        )

        return BackupCreateResponse(
            id=backup.id,
            created_at=backup.created_at,
            description=backup.description,
            exported_by=backup.exported_by,
            encrypted=backup.encrypted,
            networks_count=len(export_data.networks),
            devices_count=sum(len(network.devices) for network in export_data.networks),
            locations_count=sum(
                len(network.locations) for network in export_data.networks
            ),
            password=password if encrypt else None,
            backup_data=final_data,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create backup: {str(e)}",
        ) from None


@router.post("/restore", response_model=BackupRestoreResponse)
async def restore_backup(
    _: Annotated[None, Depends(require_master_session)],
    db: Annotated[AsyncSession, Depends(get_db)],
    request: BackupRestoreRequest,
) -> BackupRestoreResponse:
    """Restore networks, locations, and devices from backup data.

    Args:
        request: Restore request containing backup data and options
        db: Database session

    Returns:
        BackupRestoreResponse with restore results
    """
    try:
        # Parse backup data
        backup_data = request.backup_data

        # Decrypt if needed
        if backup_data.get("encrypted"):
            if not request.password:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Password is required for encrypted backup",
                )
            json_data = decrypt_data(backup_data, request.password)
            export_data_dict = json.loads(json_data)
        else:
            export_data_dict = backup_data

        # Validate export data format
        from app.schemas.export import ExportData

        export_data = ExportData.model_validate(export_data_dict)

        # Perform restore
        export_service = ExportImportService(db)
        results = await export_service.import_networks(
            export_data=export_data,
            imported_by="api",
            overwrite_existing=request.overwrite_existing,
        )

        # Create audit record
        backup_service = BackupService(db)
        await backup_service.create_restore_record(
            networks_restored=results["networks_created"],
            networks_updated=results["networks_updated"],
            locations_created=results["locations_created"],
            devices_created=results["devices_created"],
            errors=results["errors"],
        )

        return BackupRestoreResponse(
            success=len(results["errors"]) == 0,
            networks_created=results["networks_created"],
            networks_updated=results["networks_updated"],
            locations_created=results["locations_created"],
            devices_created=results["devices_created"],
            errors=results["errors"],
        )

    except BusinessRuleViolationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.message,
        ) from None
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restore backup: {str(e)}",
        ) from None


@router.post("/upload")
async def upload_backup_file(
    _: Annotated[None, Depends(require_master_session)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile,
    password: str = "",
    overwrite_existing: bool = False,
    dry_run: bool = False,
) -> JSONResponse:
    """Upload and optionally restore from a backup file.

    Args:
        file: Backup file to upload
        password: Password for encrypted backup
        overwrite_existing: Whether to overwrite existing networks
        dry_run: If True, only parse and validate without restoring
        db: Database session

    Returns:
        JSON response with backup info or restore results
    """
    if not file.filename or not file.filename.endswith(".json"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JSON files are supported for backup",
        )

    try:
        content = await file.read()
        backup_data = json.loads(content.decode("utf-8"))

        # Get backup info
        backup_info = await _get_backup_info(backup_data, password)

        if dry_run:
            return JSONResponse(
                content={
                    "dry_run": True,
                    "backup_info": backup_info,
                    "message": "Backup file is valid. Use POST /backup/restore to restore.",
                }
            )

        # Perform restore
        restore_request = BackupRestoreRequest(
            backup_data=backup_data,
            password=password if backup_data.get("encrypted") else None,
            overwrite_existing=overwrite_existing,
        )

        restore_response = await restore_backup(db, restore_request)

        return JSONResponse(
            content={
                "backup_info": backup_info,
                "restore_results": restore_response.model_dump(),
            }
        )

    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON file: {str(e)}",
        ) from None
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error processing backup file: {str(e)}",
        ) from None


@router.get("/info")
async def get_backup_info_from_data(
    _: Annotated[None, Depends(require_master_session)],
    backup_data: dict[str, Any],
    password: str = "",
) -> BackupInfoResponse:
    """Get information about backup data without restoring it.

    Args:
        backup_data: Backup data to analyze
        password: Password for encrypted backup

    Returns:
        BackupInfoResponse with backup details
    """
    return BackupInfoResponse(**await _get_backup_info(backup_data, password))


async def _get_backup_info(
    backup_data: dict[str, Any], password: str = ""
) -> dict[str, Any]:
    """Extract information from backup data."""
    try:
        if backup_data.get("encrypted"):
            if not password:
                return {
                    "encrypted": True,
                    "version": backup_data.get("version", "Unknown"),
                    "error": "Password required to view encrypted backup contents",
                }

            json_data = decrypt_data(backup_data, password)
            export_data_dict = json.loads(json_data)
        else:
            export_data_dict = backup_data

        # Parse export data
        from app.schemas.export import ExportData

        export_data = ExportData.model_validate(export_data_dict)

        networks_count = len(export_data.networks)
        devices_count = sum(len(network.devices) for network in export_data.networks)
        locations_count = sum(
            len(network.locations) for network in export_data.networks
        )

        network_details = [
            {
                "name": network.name,
                "cidr": network.network_cidr,
                "devices_count": len(network.devices),
                "locations_count": len(network.locations),
            }
            for network in export_data.networks
        ]

        return {
            "encrypted": backup_data.get("encrypted", False),
            "version": export_data.metadata.version,
            "exported_at": export_data.metadata.exported_at,
            "exported_by": export_data.metadata.exported_by,
            "description": export_data.metadata.description,
            "networks_count": networks_count,
            "locations_count": locations_count,
            "devices_count": devices_count,
            "networks": network_details,
        }

    except Exception as e:
        return {
            "encrypted": backup_data.get("encrypted", False),
            "error": f"Error parsing backup: {str(e)}",
        }
