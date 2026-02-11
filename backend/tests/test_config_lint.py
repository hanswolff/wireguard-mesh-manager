"""Tests for the config lint endpoint."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.schemas.config_lint import ConfigLintRequest, DeviceLint, LocationLint

if TYPE_CHECKING:
    from httpx import AsyncClient


async def test_config_lint_valid_config(async_client: AsyncClient) -> None:
    """Test lint with a valid configuration."""
    config = ConfigLintRequest(
        network_cidr="10.0.0.0/24",
        dns_servers="8.8.8.8,1.1.1.1",
        mtu=1420,
        persistent_keepalive=25,
        public_key="ElVVjfWGrieQB//6J+wXRR0VB/esVEKt2f+8Bw+fYjs=",  # pragma: allowlist secret
        locations=[
            LocationLint(
                name="Office",
                description="Main office location",
                external_endpoint="office.example.com",
            )
        ],
        devices=[
            DeviceLint(
                name="laptop-john",
                description="John's work laptop",
                wireguard_ip="10.0.0.2",
                public_key="4l3Np6fFE9MctGlye9QoPI2XXxd4+x76tOKNKnYf2gE=",  # pragma: allowlist secret
                enabled=True,
            )
        ],
    )

    response = await async_client.post("/api/config-lint", json=config.model_dump())
    assert response.status_code == 200

    result = response.json()
    assert result["valid"] is True
    assert result["issue_count"]["error"] == 0
    assert len(result["issues"]) == 0
    assert "valid with no issues" in result["summary"].lower()


async def test_config_lint_invalid_cidr(async_client: AsyncClient) -> None:
    """Test lint with invalid network CIDR."""
    config = ConfigLintRequest(network_cidr="invalid.cidr")

    response = await async_client.post("/api/config-lint", json=config.model_dump())
    assert response.status_code == 200

    result = response.json()
    assert result["valid"] is False
    assert result["issue_count"]["error"] > 0

    # Check that we have an error about the CIDR
    cidr_errors = [
        issue for issue in result["issues"] if issue["field"] == "network_cidr"
    ]
    assert len(cidr_errors) > 0
    assert any("invalid" in issue["message"].lower() for issue in cidr_errors)


async def test_config_lint_duplicate_device_ips(async_client: AsyncClient) -> None:
    """Test lint with duplicate device IP addresses."""
    config = ConfigLintRequest(
        network_cidr="10.0.0.0/24",
        devices=[
            DeviceLint(
                name="device1",
                wireguard_ip="10.0.0.2",
                public_key="ElVVjfWGrieQB//6J+wXRR0VB/esVEKt2f+8Bw+fYjs=",  # pragma: allowlist secret
            ),
            DeviceLint(
                name="device2",
                wireguard_ip="10.0.0.2",  # Same IP as device1
                public_key="4l3Np6fFE9MctGlye9QoPI2XXxd4+x76tOKNKnYf2gE=",  # pragma: allowlist secret
            ),
        ],
    )

    response = await async_client.post("/api/config-lint", json=config.model_dump())
    assert response.status_code == 200

    result = response.json()
    assert result["valid"] is False
    assert result["issue_count"]["error"] > 0

    # Check that we have an error about duplicate IPs
    duplicate_ip_errors = [
        issue
        for issue in result["issues"]
        if issue["field"] == "wireguard_ip" and "duplicate" in issue["message"].lower()
    ]
    assert len(duplicate_ip_errors) > 0


async def test_config_lint_device_ip_outside_network(async_client: AsyncClient) -> None:
    """Test lint with device IP outside network range."""
    config = ConfigLintRequest(
        network_cidr="10.0.0.0/24",
        devices=[
            DeviceLint(
                name="device1",
                wireguard_ip="192.168.1.100",  # Outside 10.0.0.0/24
                public_key="ElVVjfWGrieQB//6J+wXRR0VB/esVEKt2f+8Bw+fYjs=",  # pragma: allowlist secret
            )
        ],
    )

    response = await async_client.post("/api/config-lint", json=config.model_dump())
    assert response.status_code == 200

    result = response.json()
    assert result["valid"] is False
    assert result["issue_count"]["error"] > 0

    # Check that we have an error about IP being outside network
    network_errors = [
        issue
        for issue in result["issues"]
        if issue["field"] == "wireguard_ip" and "not in network" in issue["message"]
    ]
    assert len(network_errors) > 0


async def test_config_lint_invalid_public_key(async_client: AsyncClient) -> None:
    """Test lint with invalid public key format."""
    config = ConfigLintRequest(
        network_cidr="10.0.0.0/24",
        devices=[
            DeviceLint(name="device1", public_key="invalid-key")  # Not 44 chars base64
        ],
    )

    response = await async_client.post("/api/config-lint", json=config.model_dump())
    assert response.status_code == 200

    result = response.json()
    assert result["valid"] is False
    assert result["issue_count"]["error"] > 0

    # Check that we have an error about invalid public key
    key_errors = [
        issue
        for issue in result["issues"]
        if issue["field"] == "public_key" and "public key" in issue["message"].lower()
    ]
    assert len(key_errors) > 0


async def test_config_lint_warnings_and_info(async_client: AsyncClient) -> None:
    """Test lint that generates warnings and info messages."""
    config = ConfigLintRequest(
        network_cidr="10.0.0.0/30",  # Very small network - should trigger warning
        locations=[
            LocationLint(
                name="Office",
                external_endpoint="invalid:endpoint",  # Invalid endpoint - should trigger warning
            )
        ],
        # No devices - should trigger info
    )

    response = await async_client.post("/api/config-lint", json=config.model_dump())
    assert response.status_code == 200

    result = response.json()
    assert result["issue_count"]["warning"] > 0 or result["issue_count"]["info"] > 0
    assert len(result["issues"]) > 0

    # Should have warnings/errors about small network and invalid endpoint
    categories = {issue["category"] for issue in result["issues"]}
    assert any(cat in categories for cat in ["location", "general", "network"])


async def test_config_lint_duplicate_names(async_client: AsyncClient) -> None:
    """Test lint with duplicate location and device names."""
    config = ConfigLintRequest(
        network_cidr="10.0.0.0/24",
        locations=[
            LocationLint(name="Office"),
            LocationLint(name="Office"),
        ],  # Duplicate name
        devices=[
            DeviceLint(
                name="laptop",
                public_key="ElVVjfWGrieQB//6J+wXRR0VB/esVEKt2f+8Bw+fYjs=",  # pragma: allowlist secret
            ),
            DeviceLint(
                name="laptop",  # Duplicate name
                public_key="4l3Np6fFE9MctGlye9QoPI2XXxd4+x76tOKNKnYf2gE=",  # pragma: allowlist secret
            ),
        ],
    )

    response = await async_client.post("/api/config-lint", json=config.model_dump())
    assert response.status_code == 200

    result = response.json()
    assert result["valid"] is False
    assert result["issue_count"]["error"] >= 2  # At least 2 errors for duplicates

    # Check that we have errors about duplicate names
    duplicate_errors = [
        issue for issue in result["issues"] if "duplicate" in issue["message"].lower()
    ]
    assert len(duplicate_errors) >= 2


async def test_config_lint_location_external_endpoint_without_port(
    async_client: AsyncClient,
) -> None:
    """Test that location external endpoint without port is accepted."""
    config = ConfigLintRequest(
        network_cidr="10.0.0.0/24",
        locations=[
            LocationLint(name="Office", external_endpoint="office.example.com"),
            LocationLint(name="Datacenter", external_endpoint="192.168.1.100"),
            LocationLint(name="Cloud", external_endpoint="1.2.3.4"),
        ],
    )

    response = await async_client.post("/api/config-lint", json=config.model_dump())
    assert response.status_code == 200

    result = response.json()
    # Should be valid since all endpoints are hostname/IP without port
    assert result["valid"] is True
    assert result["issue_count"]["error"] == 0


async def test_config_lint_location_external_endpoint_with_port_rejected(
    async_client: AsyncClient,
) -> None:
    """Test that location external endpoint with port is rejected."""
    config = ConfigLintRequest(
        network_cidr="10.0.0.0/24",
        locations=[
            LocationLint(
                name="Office", external_endpoint="office.example.com:51820"
            ),
        ],
    )

    response = await async_client.post("/api/config-lint", json=config.model_dump())
    assert response.status_code == 200

    result = response.json()
    # Should have warning about port in location external_endpoint
    assert result["issue_count"]["warning"] > 0

    location_errors = [
        issue
        for issue in result["issues"]
        if issue["field"] == "external_endpoint"
        and issue["category"] == "location"
    ]
    assert len(location_errors) > 0
    assert any("external endpoint" in issue["message"].lower() for issue in location_errors)


async def test_config_lint_location_external_endpoint_invalid_hostname(
    async_client: AsyncClient,
) -> None:
    """Test that invalid location external endpoint is rejected."""
    config = ConfigLintRequest(
        network_cidr="10.0.0.0/24",
        locations=[
            LocationLint(name="Office", external_endpoint="-invalid.hostname"),
        ],
    )

    response = await async_client.post("/api/config-lint", json=config.model_dump())
    assert response.status_code == 200

    result = response.json()
    # Should have warning about invalid external_endpoint
    assert result["issue_count"]["warning"] > 0

    location_errors = [
        issue
        for issue in result["issues"]
        if issue["field"] == "external_endpoint"
        and issue["category"] == "location"
    ]
    assert len(location_errors) > 0

