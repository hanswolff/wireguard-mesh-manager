"""API routes for health, readiness, and metrics endpoints."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.connection import get_db
from app.services.metrics import MetricsService
from app.utils.logging import get_logger

router = APIRouter(tags=["health"])
logger = get_logger(__name__)
PROCESS_START_TIME = time.time()


@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Health check endpoint.

    Returns basic service health status with a lightweight database probe.
    This endpoint should always return quickly.
    """
    db_status = "healthy"
    try:
        result = await db.execute(text("SELECT 1"))
        if result.scalar() != 1:
            db_status = "unhealthy"
    except Exception as exc:
        db_status = "unhealthy"
        logger.warning(
            "Health check database probe failed",
            extra={"error": str(exc)},
        )

    overall_status = "healthy" if db_status == "healthy" else "unhealthy"
    return {
        "status": overall_status,
        "service": settings.service_name,
        "version": settings.app_version,
        "timestamp": datetime.now(UTC).isoformat(),
        "uptime_seconds": int(time.time() - PROCESS_START_TIME),
        "database_status": db_status,
    }


@router.get("/ready")
async def readiness_check(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Readiness check endpoint.

    Checks if the service is ready to serve traffic by verifying
    database connectivity and other essential dependencies.
    """
    try:
        # Check database connectivity
        result = await db.execute(text("SELECT 1"))
        db_status = "healthy" if result.scalar() == 1 else "unhealthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    # Determine overall readiness
    is_ready = db_status == "healthy"

    return {
        "status": "ready" if is_ready else "not_ready",
        "service": settings.service_name,
        "checks": {
            "database": db_status,
        },
        "ready": is_ready,
    }


def get_metrics_service(request: Request) -> MetricsService:
    """Get metrics service instance from the app state."""
    metrics_middleware = getattr(request.app.state, "metrics_middleware", None)
    return MetricsService(metrics_middleware)


@router.get("/metrics")
async def get_metrics(
    request: Request,
    metrics_service: MetricsService = Depends(get_metrics_service),
) -> dict[str, Any]:
    """
    Get application metrics.

    Returns basic metrics about API usage including request counts,
    authentication failures, and average response times.
    """
    return metrics_service.get_metrics()


@router.post("/metrics/reset")
async def reset_metrics(
    metrics_service: MetricsService = Depends(get_metrics_service),
) -> dict[str, str]:
    """
    Reset all collected metrics.

    This endpoint is primarily for testing and monitoring purposes.
    """
    return metrics_service.reset_metrics()
