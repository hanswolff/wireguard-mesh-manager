"""Test database models and connections."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database.models import APIKey, AuditEvent, Device, Location, WireGuardNetwork


def generate_test_wireguard_ip() -> str:
    """Generate a unique test WireGuard IP address."""
    from uuid import uuid4

    last_octet = (int(uuid4().hex[:8], 16) % 200) + 50  # Range 50-249
    return f"10.0.1.{last_octet}"


def generate_test_public_key() -> str:
    """Generate a unique test public key."""
    from uuid import uuid4

    unique_id = uuid4().hex + uuid4().hex
    return (unique_id[:44] + "=" * 44)[:44]


@pytest.mark.asyncio
async def test_database_init(db_session, unique_network_name) -> None:
    """Test database initialization and creating all model types."""
    session = db_session
    # Test we can create a network
    network = WireGuardNetwork(
        name=unique_network_name,
        description="A test network",
        network_cidr="10.0.0.0/24",
        private_key_encrypted="encrypted_private_key",
        public_key=generate_test_public_key(),
    )
    session.add(network)
    await session.commit()
    await session.refresh(network)

    # Verify the network was created
    result = await session.execute(
        select(WireGuardNetwork).where(WireGuardNetwork.name == unique_network_name)
    )
    db_network = result.scalar_one()
    assert db_network.name == unique_network_name
    assert db_network.network_cidr == "10.0.0.0/24"

    # Test we can create a location
    location = Location(
        network_id=network.id,
        name="Test Location",
        description="A test location",
        external_endpoint="example.com:51820",
    )
    session.add(location)
    await session.commit()
    await session.refresh(location)

    # Verify the location was created
    result = await session.execute(
        select(Location).where(Location.name == "Test Location")
    )
    db_location = result.scalar_one()
    assert db_location.name == "Test Location"
    assert db_location.network_id == network.id

    # Test we can create a device
    test_ip = generate_test_wireguard_ip()
    device = Device(
        network_id=network.id,
        location_id=location.id,
        name="Test Device",
        description="A test device",
        wireguard_ip=test_ip,
        private_key_encrypted="encrypted_device_private_key",
        public_key=generate_test_public_key(),
        enabled=True,
    )
    session.add(device)
    await session.commit()
    await session.refresh(device)

    # Verify the device was created
    result = await session.execute(select(Device).where(Device.name == "Test Device"))
    db_device = result.scalar_one()
    assert db_device.name == "Test Device"
    assert db_device.network_id == network.id
    assert db_device.location_id == location.id
    assert db_device.wireguard_ip == test_ip

    # Test we can create an API key
    api_key = APIKey(
        network_id=network.id,
        device_id=device.id,
        key_hash="test_hash_value_1234567890123456789012345678901234567890123456789012345678901234",
        key_fingerprint="test_hash_value_1234567890123456789012345678901234567890123456789012345678901234",
        name="Test API Key",
        allowed_ip_ranges='["10.0.0.0/24"]',
        enabled=True,
    )
    session.add(api_key)
    await session.commit()
    await session.refresh(api_key)

    # Verify the API key was created
    result = await session.execute(select(APIKey).where(APIKey.name == "Test API Key"))
    db_api_key = result.scalar_one()
    assert db_api_key.name == "Test API Key"
    assert db_api_key.network_id == network.id
    assert db_api_key.device_id == device.id

    # Test we can create an audit event
    audit_event = AuditEvent(
        network_id=network.id,
        actor="test@example.com",
        action="CREATE",
        resource_type="device",
        resource_id=device.id,
        details='{"test": "data"}',
    )
    session.add(audit_event)
    await session.commit()
    await session.refresh(audit_event)

    # Verify the audit event was created
    result = await session.execute(
        select(AuditEvent).where(AuditEvent.action == "CREATE")
    )
    db_audit_event = result.scalar_one()
    assert db_audit_event.network_id == network.id
    assert db_audit_event.actor == "test@example.com"
    assert db_audit_event.action == "CREATE"
    assert db_audit_event.resource_id == device.id


@pytest.mark.asyncio
async def test_model_relationships(db_session, unique_network_name) -> None:
    """Test model relationships work correctly."""
    session = db_session
    # Create network
    network = WireGuardNetwork(
        name=unique_network_name,
        description="A test network",
        network_cidr="10.0.0.0/24",
        private_key_encrypted="encrypted_private_key",
        public_key=generate_test_public_key(),
    )
    session.add(network)
    await session.commit()

    # Test relationship to locations
    location = Location(
        network_id=network.id,
        name="Test Location",
        description="A test location",
    )
    session.add(location)
    await session.commit()

    # Load network and test relationships - use eager loading to avoid lazy loading issues
    result = await session.execute(
        select(WireGuardNetwork)
        .options(selectinload(WireGuardNetwork.locations))
        .where(WireGuardNetwork.id == network.id)
    )
    db_network = result.scalar_one()
    assert len(db_network.locations) == 1
    assert db_network.locations[0].name == "Test Location"
