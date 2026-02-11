"""Request hardening middleware for security."""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.config import settings

if TYPE_CHECKING:
    from starlette.types import ASGIApp


class RequestSizeMiddleware(BaseHTTPMiddleware):
    """Middleware to limit request body size."""

    def __init__(self, app: ASGIApp, max_size: int = settings.max_request_size):
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Check content-length header before processing request."""
        content_length = request.headers.get("content-length")

        if content_length:
            try:
                content_length_value = int(content_length)
            except ValueError:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "error": "invalid_content_length",
                        "message": "Content-Length header must be a valid integer",
                    },
                )
            if content_length_value < 0:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "error": "invalid_content_length",
                        "message": "Content-Length header must be non-negative",
                    },
                )
            if content_length_value > self.max_size:
                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content={
                        "error": "request_too_large",
                        "message": f"Request body too large. Maximum size is {self.max_size} bytes",
                        "max_size": self.max_size,
                    },
                )

        return await call_next(request)


class RequestTimeoutMiddleware(BaseHTTPMiddleware):
    """Middleware to monitor request processing time."""

    def __init__(self, app: ASGIApp, timeout: int = settings.request_timeout):
        super().__init__(app)
        self.timeout = timeout

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Add processing time monitoring to requests."""
        start_time = time.time()

        try:
            response = await call_next(request)
            processing_time = time.time() - start_time

            # Add processing time header for monitoring
            response.headers["X-Process-Time"] = str(processing_time)

            return response
        except Exception:
            # Check if this might be a timeout scenario
            if time.time() - start_time > self.timeout:
                return JSONResponse(
                    status_code=status.HTTP_408_REQUEST_TIMEOUT,
                    content={
                        "error": "request_timeout",
                        "message": f"Request processing exceeded {self.timeout} seconds",
                        "timeout": self.timeout,
                    },
                )
            raise


class StrictJSONMiddleware(BaseHTTPMiddleware):
    """Middleware for strict JSON parsing and validation."""

    def __init__(
        self,
        app: ASGIApp,
        max_depth: int = settings.max_json_depth,
        max_string_length: int = settings.max_string_length,
        max_items_per_array: int = settings.max_items_per_array,
    ):
        super().__init__(app)
        self.max_depth = max_depth
        self.max_string_length = max_string_length
        self.max_items_per_array = max_items_per_array

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Validate JSON payload before processing."""
        if request.method in {"POST", "PUT", "PATCH"} and request.headers.get(
            "content-type", ""
        ).startswith("application/json"):
            try:
                body = await request.body()

                # Check total body size again as a safety net
                if len(body) > settings.max_request_size:
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={
                            "error": "request_too_large",
                            "message": f"Request body too large. Maximum size is {settings.max_request_size} bytes",
                        },
                    )

                if body:
                    # Parse and validate JSON structure
                    try:
                        json_data = json.loads(body.decode("utf-8"))
                        validation_errors = self._validate_json_structure(json_data)

                        if validation_errors:
                            return JSONResponse(
                                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                content={
                                    "error": "json_validation_error",
                                    "message": "JSON payload validation failed",
                                    "details": validation_errors,
                                },
                            )
                    except json.JSONDecodeError as e:
                        return JSONResponse(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            content={
                                "error": "invalid_json",
                                "message": f"Invalid JSON format: {str(e)}",
                            },
                        )
                    except UnicodeDecodeError:
                        return JSONResponse(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            content={
                                "error": "invalid_encoding",
                                "message": "Request body must be valid UTF-8",
                            },
                        )

            except Exception:
                # If we can't process the body, return a generic error
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "error": "body_processing_error",
                        "message": "Failed to process request body",
                    },
                )

        return await call_next(request)

    def _validate_json_structure(
        self, data: Any, depth: int = 0, path: str = "root"
    ) -> list[str]:
        """Recursively validate JSON structure and return list of validation errors."""
        errors = []

        if depth > self.max_depth:
            errors.append(f"Maximum JSON depth ({self.max_depth}) exceeded at {path}")
            return errors

        if isinstance(data, dict):
            for key, value in data.items():
                # Validate key length
                if len(key) > self.max_string_length:
                    errors.append(
                        f"Key too long at {path}.{key}: {len(key)} > {self.max_string_length}"
                    )

                # Recursively validate values
                errors.extend(
                    self._validate_json_structure(value, depth + 1, f"{path}.{key}")
                )

        elif isinstance(data, list):
            if len(data) > self.max_items_per_array:
                errors.append(
                    f"Array too large at {path}: {len(data)} > {self.max_items_per_array}"
                )

            for i, item in enumerate(data):
                errors.extend(
                    self._validate_json_structure(item, depth + 1, f"{path}[{i}]")
                )

        elif isinstance(data, str) and len(data) > self.max_string_length:
            errors.append(
                f"String too long at {path}: {len(data)} > {self.max_string_length}"
            )

        return errors


def add_request_hardening_middleware(app: FastAPI) -> None:
    """Add all request hardening middleware to the FastAPI app."""
    # Add middleware in reverse order (last added executes first)
    app.add_middleware(StrictJSONMiddleware)
    app.add_middleware(RequestTimeoutMiddleware)
    app.add_middleware(RequestSizeMiddleware)
