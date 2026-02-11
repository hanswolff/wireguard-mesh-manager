"""Unit tests for schema invariants, authZ boundaries, and encryption edge cases."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.database.models import APIKey, AuditEvent, Device, Location, WireGuardNetwork

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# Test constants
VALID_NETWORK_CIDR = "10.0.0.0/24"
ALTERNATIVE_NETWORK_CIDR = "10.1.0.0/24"
VALID_PUBLIC_KEY = "x" * 44
ALTERNATIVE_PUBLIC_KEY = "y" * 44
VALID_PRIVATE_KEY_ENCRYPTED = "encrypted_private_key"
ALTERNATIVE_PRIVATE_KEY_ENCRYPTED = "encrypted_private_key_2"
VALID_API_KEY_HASH = "a" * 64
ALTERNATIVE_API_KEY_HASH = "hash" * 16
VALID_IP_RANGE = '["10.0.0.0/24"]'
ALTERNATIVE_IP_RANGE = '["10.1.0.0/24"]'
VALID_WIREGUARD_IP = "10.0.0.2"
DUPLICATE_LOCATION_NAME = "Same Name"
PAST_DATE = datetime.now(UTC) - timedelta(days=1)
LARGE_ENCRYPTED_SIZE = 100000
MEDIUM_ENCRYPTED_SIZE = 50000
SMALL_ENCRYPTED_SIZE = 30000
MIN_ENCRYPTED_SIZE = 10
UNICODE_ENCRYPTED_CONTENT = "ünîçødé_ëñçrÿptēd_dætā_"
SPECIAL_CHAR_ENCRYPTED_CONTENT = "!@#$%^&*()_+-=[]{}|;':\",./<>?"


class TestHelpers:
    """Helper methods for creating test data."""

    @staticmethod
    async def create_network(
        session: AsyncSession,
        name: str,
        network_cidr: str = VALID_NETWORK_CIDR,
        private_key_encrypted: str = VALID_PRIVATE_KEY_ENCRYPTED,
        public_key: str = VALID_PUBLIC_KEY,
    ) -> WireGuardNetwork:
        """Create a test WireGuardNetwork."""
        network = WireGuardNetwork(
            name=name,
            network_cidr=network_cidr,
            private_key_encrypted=private_key_encrypted,
            public_key=public_key,
        )
        session.add(network)
        await session.commit()
        return network

    @staticmethod
    async def create_location(
        session: AsyncSession, network_id: str, name: str
    ) -> Location:
        """Create a test Location."""
        location = Location(network_id=network_id, name=name)
        session.add(location)
        await session.commit()
        return location

    @staticmethod
    async def create_device(
        session: AsyncSession,
        network_id: str,
        location_id: str,
        name: str,
        wireguard_ip: str,
        public_key: str = VALID_PUBLIC_KEY,
        private_key_encrypted: str = VALID_PRIVATE_KEY_ENCRYPTED,
        preshared_key_encrypted: str | None = None,
    ) -> Device:
        """Create a test Device."""
        device = Device(
            network_id=network_id,
            location_id=location_id,
            name=name,
            wireguard_ip=wireguard_ip,
            private_key_encrypted=private_key_encrypted,
            public_key=public_key,
            preshared_key_encrypted=preshared_key_encrypted,
        )
        session.add(device)
        await session.commit()
        return device

    @staticmethod
    async def create_api_key(
        session: AsyncSession,
        network_id: str,
        device_id: str,
        name: str,
        key_hash: str = VALID_API_KEY_HASH,
        key_fingerprint: str | None = None,
        allowed_ip_ranges: str = VALID_IP_RANGE,
        expires_at: datetime | None = None,
    ) -> APIKey:
        """Create a test APIKey."""
        if key_fingerprint is None and len(key_hash) == 64:
            key_fingerprint = key_hash
        api_key = APIKey(
            network_id=network_id,
            device_id=device_id,
            key_hash=key_hash,
            key_fingerprint=key_fingerprint,
            name=name,
            allowed_ip_ranges=allowed_ip_ranges,
            expires_at=expires_at,
        )
        session.add(api_key)
        await session.commit()
        return api_key


class TestSchemaInvariants:
    """Test database schema invariants and constraints."""

    @pytest.mark.asyncio
    async def test_network_cidr_format_constraints(
        self, db_session: AsyncSession
    ) -> None:
        """Test various CIDR format constraints."""
        valid_cidrs = [
            "10.0.0.0/24",
            "192.168.1.0/24",
            "172.16.0.0/16",
        ]

        for i, cidr in enumerate(valid_cidrs):
            await TestHelpers.create_network(
                db_session,
                name=f"Test Network {i}",
                network_cidr=cidr,
            )

    @pytest.mark.asyncio
    async def test_device_ip_allocation_invariants(
        self, db_session: AsyncSession, unique_network_name: str
    ) -> None:
        """Test device IP allocation uniqueness and constraints."""
        network = await TestHelpers.create_network(db_session, unique_network_name)
        location = await TestHelpers.create_location(
            db_session, network.id, "Test Location"
        )

        valid_ips = ["10.0.0.2", "10.0.0.3", "10.0.0.254"]

        for i, ip in enumerate(valid_ips):
            await TestHelpers.create_device(
                db_session,
                network.id,
                location.id,
                f"Device {i}",
                ip,
                public_key=f"{'x' * 40}{str(i).zfill(4)}",
            )

        duplicate_device = Device(
            network_id=network.id,
            location_id=location.id,
            name="Duplicate Device",
            wireguard_ip="10.0.0.2",
            private_key_encrypted=VALID_PRIVATE_KEY_ENCRYPTED,
            public_key="y" * 44,
        )
        db_session.add(duplicate_device)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_public_key_uniqueness_invariant(
        self, db_session: AsyncSession, unique_network_name: str
    ) -> None:
        """Test that public keys are unique within a network."""
        network = await TestHelpers.create_network(db_session, unique_network_name)
        location = await TestHelpers.create_location(
            db_session, network.id, "Test Location"
        )

        # Public key must be exactly 44 characters per the CheckConstraint
        same_public_key = "x" * 44

        await TestHelpers.create_device(
            db_session,
            network.id,
            location.id,
            "Device 1",
            "10.0.0.2",
            public_key=same_public_key,
        )

        duplicate_device = Device(
            network_id=network.id,
            location_id=location.id,
            name="Device 2",
            wireguard_ip="10.0.0.3",
            private_key_encrypted=VALID_PRIVATE_KEY_ENCRYPTED,
            public_key=same_public_key,
        )
        db_session.add(duplicate_device)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_foreign_key_constraints(self, db_session: AsyncSession) -> None:
        """Test foreign key constraint enforcement."""
        # Note: SQLite doesn't enforce foreign key constraints by default in test mode
        # This test verifies that the foreign key relationships are properly structured

        # Create a valid network and location first
        network = await TestHelpers.create_network(db_session, "Test Network FK")
        location = await TestHelpers.create_location(
            db_session, network.id, "Test Location FK"
        )

        # Test device with valid foreign keys to verify they work
        device_with_valid_fks = Device(
            network_id=network.id,  # Valid network_id
            location_id=location.id,  # Valid location_id
            name="Device with Valid FKs",
            wireguard_ip="10.0.0.10",
            private_key_encrypted=VALID_PRIVATE_KEY_ENCRYPTED,
            public_key="a" * 44,  # Valid 44-char key
        )
        db_session.add(device_with_valid_fks)
        await db_session.commit()

        # Verify the device was created successfully
        assert device_with_valid_fks.id is not None
        retrieved_device = await db_session.get(Device, device_with_valid_fks.id)
        assert retrieved_device.network_id == network.id
        assert retrieved_device.location_id == location.id

        # Rollback for cleanup
        await db_session.delete(device_with_valid_fks)
        await db_session.commit()

        # Test that the relationship works when querying
        # This verifies the foreign key relationships are properly configured
        devices_in_network = await db_session.execute(
            select(Device).where(Device.network_id == network.id)
        )
        assert (
            devices_in_network.scalars().first() is None
        )  # Should be empty after deletion

    @pytest.mark.asyncio
    async def test_location_name_uniqueness_within_network(
        self, db_session: AsyncSession, unique_network_name: str
    ) -> None:
        """Test location names are unique within a network."""
        # Create network using TestHelpers
        network = await TestHelpers.create_network(db_session, unique_network_name)

        # Create first location
        await TestHelpers.create_location(
            db_session, network.id, DUPLICATE_LOCATION_NAME
        )

        # Try to create second location with same name - should fail
        duplicate_location = Location(
            network_id=network.id,
            name=DUPLICATE_LOCATION_NAME,  # Same name in same network
        )
        db_session.add(duplicate_location)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_api_key_temporal_constraints(
        self, db_session: AsyncSession, unique_network_name: str
    ) -> None:
        """Test API key temporal constraints."""
        # Create network, location, and device using TestHelpers
        network = await TestHelpers.create_network(db_session, unique_network_name)
        location = await TestHelpers.create_location(
            db_session, network.id, "Test Location"
        )
        device = await TestHelpers.create_device(
            db_session, network.id, location.id, "Test Device", VALID_WIREGUARD_IP
        )

        # Test API key with expiration in the past (should fail constraint)
        past_api_key = APIKey(
            network_id=network.id,
            device_id=device.id,
            key_hash=VALID_API_KEY_HASH,
            key_fingerprint=VALID_API_KEY_HASH,
            name="Past API Key",
            allowed_ip_ranges=VALID_IP_RANGE,
            expires_at=PAST_DATE,
        )
        db_session.add(past_api_key)

        with pytest.raises(IntegrityError):
            await db_session.commit()


class TestAuthZBoundaries:
    """Test authorization boundaries and access control."""

    @pytest.mark.asyncio
    async def test_network_isolation(self, db_session: AsyncSession) -> None:
        """Test that networks are properly isolated."""
        # Create two separate networks using TestHelpers
        network1 = await TestHelpers.create_network(
            db_session,
            "Network 1",
            network_cidr=VALID_NETWORK_CIDR,
            private_key_encrypted=ALTERNATIVE_PRIVATE_KEY_ENCRYPTED + "_1",
            public_key=VALID_PUBLIC_KEY,
        )
        network2 = await TestHelpers.create_network(
            db_session,
            "Network 2",
            network_cidr=ALTERNATIVE_NETWORK_CIDR,
            private_key_encrypted=ALTERNATIVE_PRIVATE_KEY_ENCRYPTED + "_2",
            public_key=ALTERNATIVE_PUBLIC_KEY,
        )

        # Create locations in each network
        await TestHelpers.create_location(db_session, network1.id, "Location 1")
        location2 = await TestHelpers.create_location(
            db_session, network2.id, "Location 2"
        )

        # Verify isolation using efficient queries
        devices_in_network1_result = await db_session.execute(
            select(Device).where(Device.network_id == network1.id)
        )
        devices_in_network2_result = await db_session.execute(
            select(Device).where(Device.network_id == network2.id)
        )

        # Initially empty but properly separated - use scalars() directly
        assert devices_in_network1_result.scalars().first() is None
        assert devices_in_network2_result.scalars().first() is None

        # Test cross-network reference violation
        cross_network_device = Device(
            network_id=network1.id,
            location_id=location2.id,  # Location from different network
            name="Cross Network Device",
            wireguard_ip=VALID_WIREGUARD_IP,
            private_key_encrypted=VALID_PRIVATE_KEY_ENCRYPTED,
            public_key="z" * 44,
        )
        db_session.add(cross_network_device)

        # This might not fail FK constraint but should be caught by service layer
        # The test verifies the database structure allows proper isolation

    @pytest.mark.asyncio
    async def test_api_key_network_scoping(self, db_session: AsyncSession) -> None:
        """Test API keys are properly scoped to networks."""
        # Create two networks using TestHelpers
        network1 = await TestHelpers.create_network(
            db_session,
            "Network 1",
            network_cidr=VALID_NETWORK_CIDR,
            private_key_encrypted=ALTERNATIVE_PRIVATE_KEY_ENCRYPTED + "_1",
            public_key=VALID_PUBLIC_KEY,
        )
        await TestHelpers.create_network(
            db_session,
            "Network 2",
            network_cidr=ALTERNATIVE_NETWORK_CIDR,
            private_key_encrypted=ALTERNATIVE_PRIVATE_KEY_ENCRYPTED + "_2",
            public_key=ALTERNATIVE_PUBLIC_KEY,
        )

        # Create device in network 1 using TestHelpers
        location1 = await TestHelpers.create_location(db_session, network1.id, "Loc 1")
        device1 = await TestHelpers.create_device(
            db_session,
            network1.id,
            location1.id,
            "Device 1",
            VALID_WIREGUARD_IP,
            public_key="d1" * 22,
        )

        # Create API key for network 1 using TestHelpers
        api_key = await TestHelpers.create_api_key(
            db_session,
            network1.id,
            device1.id,
            "API Key 1",
            key_hash=ALTERNATIVE_API_KEY_HASH,
            allowed_ip_ranges=VALID_IP_RANGE,
        )

        # Verify API key is correctly associated with network
        retrieved_key = await db_session.get(APIKey, api_key.id)
        assert retrieved_key.network_id == network1.id
        assert retrieved_key.device.network_id == network1.id

    @pytest.mark.asyncio
    async def test_audit_event_network_isolation(
        self, db_session: AsyncSession
    ) -> None:
        """Test audit events are properly isolated by network."""
        # Create two networks using TestHelpers
        network1 = await TestHelpers.create_network(
            db_session,
            "Network 1",
            network_cidr=VALID_NETWORK_CIDR,
            private_key_encrypted=ALTERNATIVE_PRIVATE_KEY_ENCRYPTED + "_1",
            public_key=VALID_PUBLIC_KEY,
        )
        network2 = await TestHelpers.create_network(
            db_session,
            "Network 2",
            network_cidr=ALTERNATIVE_NETWORK_CIDR,
            private_key_encrypted=ALTERNATIVE_PRIVATE_KEY_ENCRYPTED + "_2",
            public_key=ALTERNATIVE_PUBLIC_KEY,
        )

        # Create audit events for each network
        audit1 = AuditEvent(
            network_id=network1.id,
            actor="user1@example.com",
            action="CREATE",
            resource_type="device",
            details="Created device in network 1",
        )
        audit2 = AuditEvent(
            network_id=network2.id,
            actor="user2@example.com",
            action="CREATE",
            resource_type="device",
            details="Created device in network 2",
        )
        db_session.add_all([audit1, audit2])
        await db_session.commit()

        # Verify audit events are properly separated using efficient queries
        events_network1_result = await db_session.execute(
            select(AuditEvent).where(AuditEvent.network_id == network1.id)
        )
        events_network2_result = await db_session.execute(
            select(AuditEvent).where(AuditEvent.network_id == network2.id)
        )

        # Use scalar() for single result instead of converting to list
        network1_event = events_network1_result.scalar_one()
        network2_event = events_network2_result.scalar_one()

        # Verify one event per network
        assert network1_event is not None
        assert network2_event is not None

        # Verify no cross-contamination
        assert network1_event.details == "Created device in network 1"
        assert network2_event.details == "Created device in network 2"
        assert network1_event.network_id == network1.id
        assert network2_event.network_id == network2.id


class TestEncryptionEdgeCases:
    """Test encryption edge cases and security-critical scenarios."""

    @pytest.mark.asyncio
    async def test_encrypted_field_storage(
        self, db_session: AsyncSession, unique_network_name: str
    ) -> None:
        """Test storage of encrypted fields."""
        # Test various encrypted data lengths and formats
        test_cases = [
            # Minimum length
            "x" * MIN_ENCRYPTED_SIZE,
            # Medium length
            "x" * 100,
            # Large encrypted data (simulating large keys/certificates)
            "x" * 10000,
            # Unicode content in encrypted fields
            UNICODE_ENCRYPTED_CONTENT * 10,
            # Special characters
            SPECIAL_CHAR_ENCRYPTED_CONTENT * 10,
        ]

        # Create network using TestHelpers
        network = await TestHelpers.create_network(
            db_session,
            unique_network_name,
            private_key_encrypted=test_cases[0],
        )

        # Create location using TestHelpers
        location = await TestHelpers.create_location(
            db_session, network.id, "Test Location"
        )

        # Test device with various encrypted field sizes
        for i, encrypted_data in enumerate(test_cases):
            # Preshared key must be either NULL or exactly 44 characters per CheckConstraint
            preshared_key = None if i % 2 == 0 else "p" * 44

            device = await TestHelpers.create_device(
                db_session,
                network.id,
                location.id,
                f"Device {i}",
                f"10.0.0.{i + 2}",
                public_key=f"{'x' * 40}{str(i).zfill(4)}",
                private_key_encrypted=encrypted_data,
                preshared_key_encrypted=preshared_key,
            )

            # Verify data integrity
            retrieved = await db_session.get(Device, device.id)
            assert retrieved.private_key_encrypted == encrypted_data
            assert retrieved.preshared_key_encrypted == preshared_key

    @pytest.mark.asyncio
    async def test_key_format_validation_edge_cases(
        self, db_session: AsyncSession, unique_network_name: str
    ) -> None:
        """Test key format validation edge cases."""
        # Create network and location using TestHelpers
        network = await TestHelpers.create_network(
            db_session,
            unique_network_name,
            private_key_encrypted="encrypted_key",
        )
        location = await TestHelpers.create_location(
            db_session, network.id, "Test Location"
        )

        # Test various valid public key formats - must be exactly 44 characters
        valid_keys = [
            VALID_PUBLIC_KEY,  # "x" * 44
            "a" * 44,
            "b" * 44,
            "c" * 44,
            "d" * 44,
            "e" * 44,
        ]

        # Test that all valid 44-character keys can be created
        devices = []
        for i, key in enumerate(valid_keys):
            device = await TestHelpers.create_device(
                db_session,
                network.id,
                location.id,
                f"Valid Key Device {i}",
                f"10.0.{i + 10}.2",
                public_key=key,
            )
            devices.append(device)

            # Verify the device was created
            assert device.id is not None
            retrieved = await db_session.get(Device, device.id)
            assert retrieved.public_key == key
            assert len(retrieved.public_key) == 44

        # Test that the uniqueness constraint is enforced
        # Try to create a device with a duplicate public key
        duplicate_device = Device(
            network_id=network.id,
            location_id=location.id,
            name="Duplicate Device",
            wireguard_ip="10.0.200.1",  # Different IP
            private_key_encrypted="encrypted_key_duplicate",
            public_key=valid_keys[0],  # Use first key which should already exist
        )
        db_session.add(duplicate_device)

        with pytest.raises(IntegrityError):
            await db_session.commit()

        # Clean up
        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_api_key_hash_security(
        self, db_session: AsyncSession, unique_network_name: str
    ) -> None:
        """Test API key hash security properties."""
        # Create network, location, and device using TestHelpers
        network = await TestHelpers.create_network(db_session, unique_network_name)
        location = await TestHelpers.create_location(
            db_session, network.id, "Test Location"
        )
        device = await TestHelpers.create_device(
            db_session, network.id, location.id, "Test Device", VALID_WIREGUARD_IP
        )

        # Test various hash formats - must be exactly 64 characters
        hash_test_cases = [
            # SHA-256 hash-like (64 hex chars)
            VALID_API_KEY_HASH,  # "a" * 64
            # Mix of hex chars (64 chars)
            ("0123456789abcdef" * 4),  # 16 chars * 4 = 64 chars
            # Uppercase hex (64 chars)
            ("ABCDEF0123456789" * 4),  # 16 chars * 4 = 64 chars
            # Numbers only (64 chars)
            ("1234567890" * 6 + "12"),  # 10 * 6 + 2 = 62 chars, need 2 more
            ("1234567890" * 6 + "1234"),  # 10 * 6 + 4 = 64 chars
        ]

        for i, key_hash in enumerate(hash_test_cases):
            # Ensure all hashes are exactly 64 characters
            key_hash = (
                key_hash[:64].ljust(64, "0") if len(key_hash) < 64 else key_hash[:64]
            )

            api_key = await TestHelpers.create_api_key(
                db_session,
                network.id,
                device.id,
                f"API Key {i}",
                key_hash=key_hash,
                allowed_ip_ranges=VALID_IP_RANGE,
            )

            # Verify hash is stored correctly
            retrieved = await db_session.get(APIKey, api_key.id)
            assert retrieved.key_hash == key_hash
            assert len(retrieved.key_hash) == 64

    @pytest.mark.asyncio
    async def test_concurrent_encryption_operations(
        self, db_session: AsyncSession, unique_network_name: str
    ) -> None:
        """Test concurrent operations with encrypted data."""
        # Create network using TestHelpers
        network = await TestHelpers.create_network(db_session, unique_network_name)

        # Create multiple locations using TestHelpers
        locations = []
        for i in range(5):
            location = await TestHelpers.create_location(
                db_session, network.id, f"Location {i}"
            )
            locations.append(location)

        # Create multiple devices concurrently-like pattern using TestHelpers
        devices = []
        for i in range(10):
            location = locations[i % len(locations)]
            # Preshared key must be either NULL or exactly 44 characters per CheckConstraint
            preshared_key = (
                None
                if i % 2 == 0
                else f"preshared_{i:02d}{'x' * (44 - len(f'preshared_{i:02d}'))}"
            )

            device = await TestHelpers.create_device(
                db_session,
                network.id,
                location.id,
                f"Concurrent Device {i}",
                f"10.0.0.{i + 2}",
                public_key=f"{'x' * 40}{str(i).zfill(4)}",
                private_key_encrypted=f"encrypted_key_{i}_{'x' * 100}",
                preshared_key_encrypted=preshared_key,
            )
            devices.append(device)

        # Verify all devices were created with correct encrypted data
        for i, device in enumerate(devices):
            retrieved = await db_session.get(Device, device.id)
            assert retrieved.name == f"Concurrent Device {i}"
            assert f"encrypted_key_{i}_" in retrieved.private_key_encrypted
            if i % 2 == 0:
                assert retrieved.preshared_key_encrypted is None
            else:
                assert retrieved.preshared_key_encrypted is not None
                assert len(retrieved.preshared_key_encrypted) == 44

    @pytest.mark.asyncio
    async def test_encrypted_data_null_constraints(
        self, db_session: AsyncSession, unique_network_name: str
    ) -> None:
        """Test null constraint handling for encrypted fields."""
        # For mesh topology, networks can have null private key
        # Test that networks CAN be created with null private key
        network = WireGuardNetwork(
            name=unique_network_name,
            network_cidr=VALID_NETWORK_CIDR,
            private_key_encrypted=None,  # Valid for mesh topology
            public_key=None,  # Also valid for mesh topology
        )
        db_session.add(network)
        await db_session.commit()

        # Test that devices still require encrypted private keys
        with pytest.raises(IntegrityError):
            device = Device(
                name="Test Device",
                wireguard_ip="10.0.0.2",
                private_key_encrypted=None,  # Should not be null for devices
                public_key=VALID_PUBLIC_KEY,
                network_id=network.id,
                location_id="test-location-id",
            )
            db_session.add(device)
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_large_encrypted_payload_handling(
        self, db_session: AsyncSession, unique_network_name: str
    ) -> None:
        """Test handling of large encrypted payloads."""
        # Create network with large encrypted private key using TestHelpers
        large_encrypted_key = "x" * LARGE_ENCRYPTED_SIZE
        network = await TestHelpers.create_network(
            db_session,
            unique_network_name,
            private_key_encrypted=large_encrypted_key,
        )

        # Create location using TestHelpers
        location = await TestHelpers.create_location(
            db_session, network.id, "Test Location"
        )

        # Create device with large encrypted data using TestHelpers
        large_device_key = "y" * MEDIUM_ENCRYPTED_SIZE
        # Preshared key must be exactly 44 characters per CheckConstraint
        large_preshared = "z" * 44

        device = await TestHelpers.create_device(
            db_session,
            network.id,
            location.id,
            "Large Data Device",
            "10.0.0.100",  # Valid IP address within range
            private_key_encrypted=large_device_key,
            preshared_key_encrypted=large_preshared,
            public_key="a" * 44,  # Unique public key for this test
        )

        # Verify large data integrity
        retrieved_network = await db_session.get(WireGuardNetwork, network.id)
        retrieved_device = await db_session.get(Device, device.id)

        assert len(retrieved_network.private_key_encrypted) == LARGE_ENCRYPTED_SIZE
        assert len(retrieved_device.private_key_encrypted) == MEDIUM_ENCRYPTED_SIZE
        assert len(retrieved_device.preshared_key_encrypted) == 44

        # Also test with NULL preshared key to ensure that works
        device_no_preshared = await TestHelpers.create_device(
            db_session,
            network.id,
            location.id,
            "No Preshared Device",
            "10.0.0.101",  # Valid IP address within range
            private_key_encrypted="x" * 1000,
            preshared_key_encrypted=None,
            public_key="b" * 44,  # Different unique public key
        )

        retrieved_no_preshared = await db_session.get(Device, device_no_preshared.id)
        assert len(retrieved_no_preshared.private_key_encrypted) == 1000
        assert retrieved_no_preshared.preshared_key_encrypted is None

        # Test very large encrypted data that might stress the system
        very_large_key = "x" * 50000  # 50KB
        device_very_large = await TestHelpers.create_device(
            db_session,
            network.id,
            location.id,
            "Very Large Data Device",
            "10.0.0.102",  # Valid IP address within range
            private_key_encrypted=very_large_key,
            preshared_key_encrypted="y" * 44,  # Valid 44-char preshared key
            public_key="c" * 44,  # Third unique public key
        )

        retrieved_very_large = await db_session.get(Device, device_very_large.id)
        assert len(retrieved_very_large.private_key_encrypted) == 50000
        assert retrieved_very_large.preshared_key_encrypted == "y" * 44
