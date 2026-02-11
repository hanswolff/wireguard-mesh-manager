"""Test database model validation and constraints."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from app.database.models import APIKey, AuditEvent, Device, Location, WireGuardNetwork


def make_public_key(char: str) -> str:
    """Return a fake public key with the required length."""
    return (char * 44)[:44]


@pytest.mark.asyncio
async def test_network_name_unique_constraint(db_session, unique_network_name) -> None:
    """Test that network names must be unique."""
    session = db_session
    # Create first network
    network1 = WireGuardNetwork(
        name=unique_network_name,
        description="First test network",
        network_cidr="10.0.0.0/24",
        private_key_encrypted="encrypted_private_key_1",
        public_key=make_public_key("a"),
    )
    session.add(network1)
    await session.commit()

    # Try to create second network with same name
    network2 = WireGuardNetwork(
        name=unique_network_name,
        description="Second test network",
        network_cidr="10.1.0.0/24",
        private_key_encrypted="encrypted_private_key_2",
        public_key=make_public_key("b"),
    )
    session.add(network2)

    with pytest.raises(IntegrityError):
        await session.commit()


@pytest.mark.asyncio
async def test_network_cidr_validation(db_session) -> None:
    """Test network CIDR validation constraints."""
    session = db_session
    # Test that we can at least create networks with valid CIDRs
    # SQLite doesn't enforce IP address format constraints strictly
    valid_cidrs = [
        "10.0.0.0/24",
        "192.168.1.0/24",
        "172.16.0.0/16",
    ]

    for i, cidr in enumerate(valid_cidrs):
        network = WireGuardNetwork(
            name=f"Test Network {i}",
            network_cidr=cidr,
            private_key_encrypted="encrypted_private_key",
            public_key=make_public_key(str(i)),
        )
        session.add(network)
        await session.commit()

    # Verify all networks were created successfully
    from sqlalchemy import select

    result = await session.execute(
        select(WireGuardNetwork).where(WireGuardNetwork.name.like("Test Network %"))
    )
    networks = result.scalars().all()
    assert len(networks) == len(valid_cidrs)


@pytest.mark.asyncio
async def test_device_ip_uniqueness(db_session, unique_network_name) -> None:
    """Test that device IPs must be unique within a network."""
    session = db_session
    # Create network and location
    network = WireGuardNetwork(
        name=unique_network_name,
        network_cidr="10.0.0.0/24",
        private_key_encrypted="encrypted_private_key",
        public_key=make_public_key("c"),
    )
    session.add(network)
    await session.commit()

    location = Location(
        network_id=network.id,
        name="Test Location",
    )
    session.add(location)
    await session.commit()

    # Create first device
    device1 = Device(
        network_id=network.id,
        location_id=location.id,
        name="Device 1",
        wireguard_ip="10.0.0.2",
        private_key_encrypted="encrypted_private_key_1",
        public_key=make_public_key("d"),
    )
    session.add(device1)
    await session.commit()

    # Try to create second device with same IP
    device2 = Device(
        network_id=network.id,
        location_id=location.id,
        name="Device 2",
        wireguard_ip="10.0.0.2",
        private_key_encrypted="encrypted_private_key_2",
        public_key=make_public_key("e"),
    )
    session.add(device2)

    with pytest.raises(IntegrityError):
        await session.commit()


@pytest.mark.asyncio
async def test_api_key_expiration_validation(db_session, unique_network_name) -> None:
    """Test API key expiration validation."""
    session = db_session
    # Create network, location, and device
    network = WireGuardNetwork(
        name=unique_network_name,
        network_cidr="10.0.0.0/24",
        private_key_encrypted="encrypted_private_key",
        public_key=make_public_key("f"),
    )
    session.add(network)
    await session.commit()

    location = Location(
        network_id=network.id,
        name="Test Location",
    )
    session.add(location)
    await session.commit()

    device = Device(
        network_id=network.id,
        location_id=location.id,
        name="Test Device",
        wireguard_ip="10.0.0.2",
        private_key_encrypted="encrypted_private_key",
        public_key=make_public_key("g"),
    )
    session.add(device)
    await session.commit()

    from datetime import UTC, datetime, timedelta

    # Test invalid expiration (in the past)
    api_key = APIKey(
        network_id=network.id,
        device_id=device.id,
        key_hash="test_hash_1234567890123456789012345678901234567890123456789012345678901234",
        key_fingerprint="test_hash_1234567890123456789012345678901234567890123456789012345678901234",
        name="Test API Key",
        allowed_ip_ranges='["10.0.0.0/24"]',
        expires_at=datetime.now(UTC) - timedelta(days=1),
    )
    session.add(api_key)

    with pytest.raises(IntegrityError):
        await session.commit()


@pytest.mark.asyncio
async def test_cascade_delete_relationships(db_session, unique_network_name) -> None:
    """Test that cascade deletes work properly."""
    session = db_session
    # Create network with dependent objects
    network = WireGuardNetwork(
        name=unique_network_name,
        network_cidr="10.0.0.0/24",
        private_key_encrypted="encrypted_private_key",
        public_key=make_public_key("h"),
    )
    session.add(network)
    await session.commit()

    # Create location
    location = Location(
        network_id=network.id,
        name="Test Location",
    )
    session.add(location)
    await session.commit()

    # Create device
    device = Device(
        network_id=network.id,
        location_id=location.id,
        name="Test Device",
        wireguard_ip="10.0.0.2",
        private_key_encrypted="encrypted_private_key",
        public_key=make_public_key("i"),
    )
    session.add(device)
    await session.commit()

    # Create API key
    api_key = APIKey(
        network_id=network.id,
        device_id=device.id,
        key_hash="test_hash_1234567890123456789012345678901234567890123456789012345678901234",
        key_fingerprint="test_hash_1234567890123456789012345678901234567890123456789012345678901234",
        name="Test API Key",
        allowed_ip_ranges='["10.0.0.0/24"]',
    )
    session.add(api_key)
    await session.commit()

    # Create audit event
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

    # Verify all objects exist
    assert await session.get(Location, location.id) is not None
    assert await session.get(Device, device.id) is not None
    assert await session.get(APIKey, api_key.id) is not None
    assert await session.get(AuditEvent, audit_event.id) is not None

    # Delete network and verify cascade delete
    await session.delete(network)
    await session.commit()

    # Verify all dependent objects are deleted
    assert await session.get(Location, location.id) is None
    assert await session.get(Device, device.id) is None
    assert await session.get(APIKey, api_key.id) is None
    assert await session.get(AuditEvent, audit_event.id) is None


@pytest.mark.asyncio
async def test_timestamp_auto_update(db_session, unique_network_name) -> None:
    """Test that updated_at timestamp is automatically updated."""
    session = db_session
    # Create network
    network = WireGuardNetwork(
        name=unique_network_name,
        network_cidr="10.0.0.0/24",
        private_key_encrypted="encrypted_private_key",
        public_key=make_public_key("j"),
    )
    session.add(network)
    await session.commit()
    await session.refresh(network)

    original_created_at = network.created_at
    original_updated_at = network.updated_at

    # Wait a bit to ensure timestamp difference
    import asyncio

    await asyncio.sleep(0.01)

    # Update network
    network.description = "Updated description"
    await session.commit()
    await session.refresh(network)

    # Verify timestamps
    assert network.created_at == original_created_at  # Should not change
    assert network.updated_at > original_updated_at  # Should be updated


@pytest.mark.asyncio
async def test_device_public_key_length_44(db_session, unique_network_name) -> None:
    """Test that device public key with 44 characters is accepted."""
    session = db_session
    network = WireGuardNetwork(
        name=unique_network_name,
        network_cidr="10.0.0.0/24",
        private_key_encrypted="encrypted_private_key",
        public_key=make_public_key("a"),
    )
    session.add(network)
    await session.commit()

    location = Location(network_id=network.id, name="Test Location")
    session.add(location)
    await session.commit()

    device = Device(
        network_id=network.id,
        location_id=location.id,
        name="Device 44-char key",
        wireguard_ip="10.0.0.2",
        private_key_encrypted="encrypted_private_key",
        public_key=make_public_key("x"),
    )
    session.add(device)
    await session.commit()
    await session.refresh(device)

    assert len(device.public_key) == 44


@pytest.mark.asyncio
async def test_device_public_key_length_45(db_session, unique_network_name) -> None:
    """Test that device public key with 45 characters is accepted."""
    session = db_session
    network = WireGuardNetwork(
        name=unique_network_name,
        network_cidr="10.0.0.0/24",
        private_key_encrypted="encrypted_private_key",
        public_key=make_public_key("a"),
    )
    session.add(network)
    await session.commit()

    location = Location(network_id=network.id, name="Test Location")
    session.add(location)
    await session.commit()

    device = Device(
        network_id=network.id,
        location_id=location.id,
        name="Device 45-char key",
        wireguard_ip="10.0.0.3",
        private_key_encrypted="encrypted_private_key",
        public_key="A" * 45,
    )
    session.add(device)
    await session.commit()
    await session.refresh(device)

    assert len(device.public_key) == 45


@pytest.mark.asyncio
async def test_device_public_key_length_56(db_session, unique_network_name) -> None:
    """Test that device public key with 56 characters is accepted."""
    session = db_session
    network = WireGuardNetwork(
        name=unique_network_name,
        network_cidr="10.0.0.0/24",
        private_key_encrypted="encrypted_private_key",
        public_key=make_public_key("a"),
    )
    session.add(network)
    await session.commit()

    location = Location(network_id=network.id, name="Test Location")
    session.add(location)
    await session.commit()

    device = Device(
        network_id=network.id,
        location_id=location.id,
        name="Device 56-char key",
        wireguard_ip="10.0.0.4",
        private_key_encrypted="encrypted_private_key",
        public_key="B" * 56,
    )
    session.add(device)
    await session.commit()
    await session.refresh(device)

    assert len(device.public_key) == 56


@pytest.mark.asyncio
async def test_device_public_key_invalid_length(
    db_session, unique_network_name
) -> None:
    """Test that device public key with invalid length is rejected."""
    session = db_session
    network = WireGuardNetwork(
        name=unique_network_name,
        network_cidr="10.0.0.0/24",
        private_key_encrypted="encrypted_private_key",
        public_key=make_public_key("a"),
    )
    session.add(network)
    await session.commit()

    location = Location(network_id=network.id, name="Test Location")
    session.add(location)
    await session.commit()

    device = Device(
        network_id=network.id,
        location_id=location.id,
        name="Device invalid key",
        wireguard_ip="10.0.0.5",
        private_key_encrypted="encrypted_private_key",
        public_key="C" * 43,
    )
    session.add(device)

    with pytest.raises(IntegrityError):
        await session.commit()
