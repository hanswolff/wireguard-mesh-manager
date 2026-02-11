"""WireGuard Mesh Manager Backend API."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.middleware import (
    LoggingMiddleware,
    MetricsMiddleware,
    RateLimitMiddleware,
    add_csrf_middleware,
    add_exception_handlers,
    add_request_hardening_middleware,
    add_response_hardening_middleware,
)
from app.middleware.auth import AuthenticationMiddleware
from app.routers import api_router
from app.utils.logging import get_logger, setup_logging

# Setup structured logging
setup_logging(level=settings.log_level, service_name=settings.service_name)
logger = get_logger(__name__)
logger.info(
    "Starting WireGuard Mesh Manager API",
    extra={
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "debug": settings.debug,
        "log_level": settings.log_level,
    },
)

app = FastAPI(
    title=settings.app_name,
    description="Backend API for managing WireGuard VPN networks and devices",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add logging middleware first (to capture all requests)
app.add_middleware(LoggingMiddleware)

# Add authentication middleware early to ensure user is set for all requests
app.add_middleware(AuthenticationMiddleware)

# Add metrics middleware next (to capture all requests)
metrics_middleware = MetricsMiddleware(app)
app.middleware("http")(metrics_middleware.dispatch)
app.state.metrics_middleware = metrics_middleware

# Database session is handled per-request
# to avoid dependency injection conflicts with FastAPI's dependency system

# Add rate limiting middleware
rate_limit_middleware = RateLimitMiddleware(
    app,
    api_key_window=settings.rate_limit_api_key_window,
    api_key_max_requests=settings.rate_limit_api_key_max_requests,
    ip_window=settings.rate_limit_ip_window,
    ip_max_requests=settings.rate_limit_ip_max_requests,
    backend=settings.rate_limit_backend,
    redis_url=settings.rate_limit_redis_url,
    redis_prefix=settings.rate_limit_redis_prefix,
)
app.middleware("http")(rate_limit_middleware.dispatch)
app.state.rate_limit_middleware = rate_limit_middleware

# Add request hardening middleware
add_request_hardening_middleware(app)

# Add response hardening middleware (applied after all other middleware)
add_response_hardening_middleware(app)

# Add CORS middleware with strict configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()
    ],
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
    expose_headers=["X-CSRF-Token"],  # Expose CSRF token header
)

# Add CSRF protection middleware
add_csrf_middleware(app)

# Add exception handlers
add_exception_handlers(app)

# Include API router (all routes at /api prefix)
app.include_router(api_router)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": settings.app_name}
