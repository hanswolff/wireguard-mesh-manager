"""Router for configuration linting."""

from __future__ import annotations

from fastapi import APIRouter

from app.schemas.config_lint import ConfigLintRequest, ConfigLintResponse
from app.services.config_lint import ConfigLintService

router = APIRouter()


@router.post("/config-lint", response_model=ConfigLintResponse)
async def lint_network_config(
    config: ConfigLintRequest,
) -> ConfigLintResponse:
    """Validate a WireGuard network configuration before deployment.

    This endpoint validates all aspects of a network configuration including:
    - Network settings (CIDR, DNS, MTU, etc.)
    - Location endpoints
    - Device IP assignments and keys
    - Cross-component relationships and conflicts

    The lint operation does not require any database entities to exist
    and can be used to validate configurations before creating them.

    Args:
        config: Network configuration to validate

    Returns:
        ConfigLintResponse with detailed validation results
    """
    service = ConfigLintService()
    return service.lint_config(config)
