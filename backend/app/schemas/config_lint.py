"""Pydantic schemas for config lint operations."""

from __future__ import annotations

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Issue severity levels."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Category(str, Enum):
    """Issue categories."""

    NETWORK = "network"
    LOCATION = "location"
    DEVICE = "device"
    GENERAL = "general"


class LocationLint(BaseModel):
    """Location data for config lint validation."""

    name: Annotated[str, Field(min_length=1, max_length=100)]
    description: str | None = None
    external_endpoint: str | None = None
    internal_endpoint: str | None = None


class DeviceLint(BaseModel):
    """Device data for config lint validation."""

    name: Annotated[str, Field(min_length=1, max_length=100)]
    description: str | None = None
    wireguard_ip: str | None = None
    public_key: str | None = None
    preshared_key: str | None = None
    enabled: bool = True


class ConfigLintRequest(BaseModel):
    """Request data for config lint validation."""

    network_cidr: Annotated[
        str, Field(description="Network CIDR notation (e.g., 10.0.0.0/24)")
    ]
    dns_servers: Annotated[
        str | None, Field(description="Comma-separated DNS servers")
    ] = None
    mtu: Annotated[
        int | None, Field(description="Maximum transmission unit (576-9000 bytes)")
    ] = None
    persistent_keepalive: Annotated[
        int | None,
        Field(description="Persistent keepalive interval in seconds (0-86400)"),
    ] = None
    public_key: Annotated[
        str | None, Field(description="WireGuard public key (base64)")
    ] = None
    locations: list[LocationLint] = []
    devices: list[DeviceLint] = []


class LintIssue(BaseModel):
    """Single validation issue found during linting."""

    severity: Severity
    category: Category
    field: str
    message: str
    suggestion: str | None = None


class ConfigLintResponse(BaseModel):
    """Response data for config lint validation."""

    valid: bool
    issue_count: dict[str, int] = {}
    issues: list[LintIssue] = []
    summary: str
