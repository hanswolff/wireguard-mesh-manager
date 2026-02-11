"""Shared helpers for network API responses."""

from __future__ import annotations

from typing import Any

from app.schemas.networks import WireGuardNetworkResponse


def network_to_response(network: Any) -> WireGuardNetworkResponse:
    """Convert a network model to response while avoiding lazy-loads."""
    location_count = 0
    device_count = 0

    if hasattr(network, "_sa_instance_state"):
        from sqlalchemy.orm.attributes import instance_state

        state = instance_state(network)
        if "locations" not in state.unloaded and network.locations is not None:
            location_count = len(network.locations)
        if "devices" not in state.unloaded and network.devices is not None:
            device_count = len(network.devices)

    return WireGuardNetworkResponse(
        id=network.id,
        name=network.name,
        description=network.description,
        network_cidr=network.network_cidr,
        dns_servers=network.dns_servers,
        mtu=network.mtu,
        persistent_keepalive=network.persistent_keepalive,
        interface_properties=network.interface_properties,
        created_at=network.created_at,
        updated_at=network.updated_at,
        location_count=location_count,
        device_count=device_count,
    )
