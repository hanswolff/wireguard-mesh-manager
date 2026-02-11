"""Database session middleware for adding database session to request state."""

from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware

if TYPE_CHECKING:
    from starlette.responses import Response


class DatabaseSessionMiddleware(BaseHTTPMiddleware):
    """Middleware to add database session to request state for audit logging."""

    async def dispatch(self, request, call_next) -> Response:
        from app.database.connection import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            request.state.db = db
            response = await call_next(request)

        return response
