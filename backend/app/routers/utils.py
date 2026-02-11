"""Common utilities for router functions."""

from __future__ import annotations

import ipaddress
from functools import lru_cache
from typing import TYPE_CHECKING, Annotated, NamedTuple, NoReturn

from fastapi import Depends, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.connection import get_db
from app.services.audit import AuditService

if TYPE_CHECKING:
    from app.database.models import APIKey, Device
    from app.services.device_config import DeviceConfigService


class DeviceAuthInfo(NamedTuple):
    """Device authentication information."""

    api_key: str | None
    source_ip: str | None
    actor: str


@lru_cache(maxsize=1)
def _parse_trusted_proxies() -> (
    tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]
):
    """Parse trusted proxy configuration into network objects.

    Returns:
        Tuple of IP network objects representing trusted proxies (cached)
    """
    if not settings.trusted_proxies.strip():
        return ()

    trusted_proxies = []
    for proxy_str in settings.trusted_proxies.split(","):
        proxy_str = proxy_str.strip()
        if not proxy_str:
            continue

        try:
            if "/" in proxy_str:
                network = ipaddress.ip_network(proxy_str, strict=False)
            else:
                network = ipaddress.ip_network(proxy_str)
            trusted_proxies.append(network)
        except ValueError:
            continue

    return tuple(trusted_proxies)


def _is_trusted_proxy(client_ip: str) -> bool:
    """Check if the client IP is in the trusted proxy list.

    Args:
        client_ip: Client IP address to check

    Returns:
        True if client IP is trusted, False otherwise
    """
    if not client_ip:
        return False

    trusted_networks = _parse_trusted_proxies()
    if not trusted_networks:
        try:
            return ipaddress.ip_address(client_ip).is_loopback
        except ValueError:
            return False

    # Special handling for TestClient
    if client_ip == "testclient":
        return any(
            str(network) == "127.0.0.1/32" or str(network) == "127.0.0.0/8"
            for network in trusted_networks
        )

    try:
        client_addr = ipaddress.ip_address(client_ip)
        return any(client_addr in network for network in trusted_networks)
    except ValueError:
        return False


def get_client_actor(request: Request) -> str:
    """Extract client actor information from request."""
    session = getattr(request.state, "master_session", None)
    if session:
        return session.actor

    source_ip = _get_source_ip(request)
    return f"ip:{source_ip}"


def _get_source_ip(request: Request) -> str:
    """Get the source IP address, considering trusted proxies.

    Args:
        request: HTTP request

    Returns:
        Source IP address as string
    """
    client_ip = request.client.host if request.client else "unknown"

    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for and _is_trusted_proxy(client_ip):
        return forwarded_for.split(",")[0].strip()

    return client_ip


def get_audit_service(db: Annotated[AsyncSession, Depends(get_db)]) -> AuditService:
    """Get audit service instance."""
    return AuditService(db)


def extract_device_auth_info(request: Request) -> DeviceAuthInfo:
    """Extract device authentication information from request."""
    source_ip = _get_source_ip(request)

    api_key = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        api_key = auth_header[7:]
    if not api_key:
        api_key = request.headers.get("X-API-Key")

    actor = get_client_actor(request)

    return DeviceAuthInfo(api_key=api_key, source_ip=source_ip, actor=actor)


def raise_request_validation_error(
    message: str, field: str | None = None
) -> NoReturn:
    """Raise a FastAPI RequestValidationError with a consistent payload."""
    loc = ["body", field] if field else ["body", "request"]
    raise RequestValidationError(
        [{"loc": loc, "msg": message, "type": "value_error"}]
    )


async def validate_device_access(
    device_id: str,
    auth_info: DeviceAuthInfo,
    config_service: DeviceConfigService,
    audit_service: AuditService,
) -> tuple[Device, "APIKey" | None, bool, str | None]:
    """Validate device access and log attempts.

    Args:
        device_id: ID of the device to access
        auth_info: Authentication information from request
        config_service: Device configuration service
        audit_service: Audit logging service

    Returns:
        Tuple of (device model, matching API key, access flag, denied reason)

    Raises:
        HTTPException: If device not found or access denied
    """
    try:
        device, matching_key, has_access, denied_reason = (
            await config_service.validate_device_access(
                device_id=device_id,
                api_key=auth_info.api_key,
                source_ip=auth_info.source_ip,
            )
        )

        if not has_access:
            # Log access denied without revealing device information.
            await audit_service.log_event(
                network_id=device.network_id,
                actor=auth_info.actor,
                action="ACCESS_DENIED",
                resource_type="device_config",
                resource_id=str(device_id),
                details={
                    "source_ip": auth_info.source_ip,
                    "has_api_key": auth_info.api_key is not None,
                    "denied_reason": denied_reason or "invalid_credentials",
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        return device, matching_key, has_access, denied_reason
    except ValueError as e:
        # Log device not found attempt
        await audit_service.log_event(
            network_id=None,
            actor=auth_info.actor,
            action="ACCESS_DENIED",
            resource_type="device_config",
            resource_id=None,
            details={
                "source_ip": auth_info.source_ip,
                "has_api_key": auth_info.api_key is not None,
                "denied_reason": "device_not_found",
            },
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except NotImplementedError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Key management system not yet implemented",
        ) from e
