"""Error handlers for the WireGuard Mesh Manager API."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.exceptions import (
    BusinessRuleViolationError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)


def _serialize_validation_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Serialize validation errors, removing non-JSON-serializable objects."""
    serializable_errors = []
    for error in errors:
        serializable_error = error.copy()
        # Remove non-serializable context objects
        if "ctx" in serializable_error:
            ctx = serializable_error["ctx"]
            if ctx is not None:
                serializable_ctx = {}
                for key, value in ctx.items():
                    if isinstance(value, Exception):
                        serializable_ctx[key] = str(value)
                    else:
                        serializable_ctx[key] = value
                serializable_error["ctx"] = serializable_ctx
        serializable_errors.append(serializable_error)
    return serializable_errors


def add_exception_handlers(app: FastAPI) -> None:
    """Add exception handlers to the FastAPI app."""

    @app.exception_handler(ResourceNotFoundError)
    async def resource_not_found_handler(
        request: Request, exc: ResourceNotFoundError
    ) -> JSONResponse:
        """Handle ResourceNotFoundError as 404."""
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "resource_not_found",
                "message": exc.message,
                "resource_type": exc.resource_type,
                "resource_id": exc.resource_id,
            },
        )

    @app.exception_handler(ResourceConflictError)
    async def resource_conflict_handler(
        request: Request, exc: ResourceConflictError
    ) -> JSONResponse:
        """Handle ResourceConflictError as 409."""
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": "resource_conflict",
                "message": exc.message,
            },
        )

    @app.exception_handler(BusinessRuleViolationError)
    async def business_rule_violation_handler(
        request: Request, exc: BusinessRuleViolationError
    ) -> JSONResponse:
        """Handle BusinessRuleViolationError as 409."""
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": "business_rule_violation",
                "message": exc.message,
                "rule": exc.rule,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle validation errors with proper formatting."""
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "validation_error",
                "message": "Request validation failed",
                "details": _serialize_validation_errors(exc.errors()),
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        """Return HTTP exceptions with their original status codes."""
        if exc.status_code == status.HTTP_404_NOT_FOUND:
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": "route_not_found",
                    "message": f"No route for {request.method} {request.url.path}",
                    "detail": exc.detail,
                },
                headers=exc.headers or {},
            )

        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers or {},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle any uncaught exceptions as 500."""
        logger.error(
            "Unhandled exception occurred",
            extra={
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
                "url": str(request.url),
                "method": request.method,
                "client_ip": request.client.host if request.client else None,
            },
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_server_error",
                "message": "An unexpected error occurred",
            },
        )
