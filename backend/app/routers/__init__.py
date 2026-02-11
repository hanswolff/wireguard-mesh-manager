"""API router package."""

from fastapi import APIRouter

from app.routers import (
    api_keys,
    audit,
    backup,
    config_lint,
    csrf,
    devices,
    device_links,
    export,
    health,
    key_rotation,
    locations,
    master_password,
    networks,
    operational_settings,
    utils,
)

api_router = APIRouter(prefix="/api")

# Core API routers
api_router.include_router(health.router, tags=["health"])
api_router.include_router(networks.router, prefix="/networks", tags=["networks"])
api_router.include_router(locations.router, prefix="/locations", tags=["locations"])
api_router.include_router(devices.router, prefix="/devices", tags=["devices"])
api_router.include_router(device_links.router, tags=["device-links"])
api_router.include_router(export.router, prefix="/export", tags=["export"])
api_router.include_router(backup.router, prefix="/backup", tags=["backup"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(config_lint.router, tags=["config-lint"])

# Additional operational routers
# Note: These routers already have their own prefixes defined, so we don't add prefixes here
api_router.include_router(api_keys.router)
api_router.include_router(key_rotation.router)
api_router.include_router(master_password.router)
api_router.include_router(operational_settings.router)

# CSRF router
api_router.include_router(csrf.router, prefix="/csrf", tags=["csrf"])


@api_router.get("/")
async def api_root() -> dict[str, str]:
    """API root endpoint."""
    return {"message": "WireGuard Mesh Manager API"}
