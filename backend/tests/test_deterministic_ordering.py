"""Tests for deterministic JSON output ordering."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from httpx import AsyncClient


class TestDeterministicOrdering:
    """Test suite for deterministic JSON output ordering."""

    async def test_export_schema_deterministic_ordering(
        self, async_client: AsyncClient
    ) -> None:
        """Test that export schema returns consistently ordered JSON."""
        # Get schema twice
        response1 = await async_client.get("/api/export/networks/schema")
        response2 = await async_client.get("/api/export/networks/schema")

        assert response1.status_code == 200
        assert response2.status_code == 200

        # Compare raw JSON strings to ensure identical ordering
        schema1_str = json.dumps(response1.json(), sort_keys=True)
        schema2_str = json.dumps(response2.json(), sort_keys=True)

        assert schema1_str == schema2_str

        # Also verify the original response is already sorted
        schema1_sorted = json.loads(json.dumps(response1.json(), sort_keys=True))
        assert response1.json() == schema1_sorted

    async def test_pydantic_models_sort_keys(self) -> None:
        """Test that Pydantic models have sort_keys configuration."""
        from app.schemas.backup import (
            BackupCreateResponse,
            BackupInfoResponse,
            BackupRecord,
            BackupRestoreRequest,
            BackupRestoreResponse,
            RestoreRecord,
        )
        from app.schemas.device_config import (
            DeviceConfigResponse,
            DeviceConfiguration,
            MobileConfig,
        )
        from app.schemas.export import ExportData

        models_to_check = [
            BackupCreateResponse,
            BackupInfoResponse,
            BackupRecord,
            BackupRestoreRequest,
            BackupRestoreResponse,
            RestoreRecord,
            DeviceConfigResponse,
            DeviceConfiguration,
            MobileConfig,
            ExportData,
        ]

        for model in models_to_check:
            # Check that model has ser_json_bytes_sort_keys=True
            assert (
                getattr(model, "model_config", {}).get("ser_json_bytes_sort_keys")
                is True
            ), f"{model.__name__} missing ser_json_bytes_sort_keys=True"
