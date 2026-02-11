"""Tests for device service with IP allocation functionality."""
from __future__ import annotations
from typing import TYPE_CHECKING
import pytest
from app.exceptions import ResourceNotFoundError
from app.schemas.devices import DeviceCreate, DeviceUpdate
from app.services.devices import DeviceService
from app.utils.key_management import decrypt_device_dek_from_json, decrypt_private_key_with_dek, derive_wireguard_public_key
from tests.conftest import AsyncSessionContext
if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.database.models import Location, WireGuardNetwork

@pytest.mark.asyncio
async def test_allocate_next_available_ip(test_network: WireGuardNetwork, test_location: Location, mock_session: AsyncSession, unlocked_master_password: str) -> None:
    """Test automatic IP allocation."""
    service = DeviceService(mock_session)
    device_data = DeviceCreate(network_id=test_network.id, location_id=test_location.id, name='test-device-1', public_key='AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=', internal_endpoint_host='192.168.1.100', internal_endpoint_port=51820)
    async with AsyncSessionContext(mock_session):
        device1 = await service.create_device(device_data)
        assert device1.wireguard_ip == '10.0.0.1'
        device_data2 = DeviceCreate(network_id=test_network.id, location_id=test_location.id, name='test-device-2', public_key='BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB=', internal_endpoint_host='192.168.1.101', internal_endpoint_port=51820)
        device2 = await service.create_device(device_data2)
        assert device2.wireguard_ip == '10.0.0.2'

@pytest.mark.asyncio
async def test_generated_keys_are_paired(test_network: WireGuardNetwork, test_location: Location, mock_session: AsyncSession, unlocked_master_password: str) -> None:
    """Generated device keys should remain cryptographically paired."""
    service = DeviceService(mock_session)
    device_data = DeviceCreate(network_id=test_network.id, location_id=test_location.id, name='keyed-device', public_key='IGNOREDPLACEHOLDERPUBLICKEYIGNOREDPLACEHOLD=', internal_endpoint_host='192.168.1.100', internal_endpoint_port=51820)
    async with AsyncSessionContext(mock_session):
        device = await service.create_device(device_data)
        device_dek = decrypt_device_dek_from_json(device.device_dek_encrypted_master, unlocked_master_password)
        decrypted_private_key = decrypt_private_key_with_dek(device.private_key_encrypted, device_dek)
        derived_public_key = derive_wireguard_public_key(decrypted_private_key)
        assert derived_public_key == device.public_key

@pytest.mark.asyncio
async def test_validate_ip_in_network(test_network: WireGuardNetwork, test_location: Location, mock_session: AsyncSession) -> None:
    """Test IP validation against network CIDR."""
    service = DeviceService(mock_session)
    async with AsyncSessionContext(mock_session):
        await service._validate_ip_in_network('10.0.0.5', test_network)
    with pytest.raises(ValueError, match='not within network CIDR'):
        await service._validate_ip_in_network('192.168.1.5', test_network)
    with pytest.raises(ValueError, match='Invalid IP address'):
        await service._validate_ip_in_network('invalid.ip', test_network)

@pytest.mark.asyncio
async def test_validate_ip_availability(test_network: WireGuardNetwork, test_location: Location, mock_session: AsyncSession, unlocked_master_password: str) -> None:
    """Test IP availability validation."""
    service = DeviceService(mock_session)
    device_data = DeviceCreate(network_id=test_network.id, location_id=test_location.id, name='test-device', wireguard_ip='10.0.0.10', public_key='AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=', internal_endpoint_host='192.168.1.100', internal_endpoint_port=51820)
    async with AsyncSessionContext(mock_session):
        device = await service.create_device(device_data)
        with pytest.raises(ValueError, match='already allocated'):
            await service._validate_ip_available('10.0.0.10', test_network.id)
        await service._validate_ip_available('10.0.0.11', test_network.id)
        await service._validate_ip_available('10.0.0.10', test_network.id, exclude_device_id=device.id)

@pytest.mark.asyncio
async def test_validate_public_key_uniqueness(test_network: WireGuardNetwork, test_location: Location, mock_session: AsyncSession, unlocked_master_password: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test public key uniqueness validation."""
    service = DeviceService(mock_session)
    deterministic_private_key = 'AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQE='
    monkeypatch.setattr('app.services.devices.generate_wireguard_private_key', lambda: deterministic_private_key)
    device_data = DeviceCreate(network_id=test_network.id, location_id=test_location.id, name='test-device-1', public_key='AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=', internal_endpoint_host='192.168.1.100', internal_endpoint_port=51820)
    async with AsyncSessionContext(mock_session):
        device1 = await service.create_device(device_data)
        device_data2 = DeviceCreate(network_id=test_network.id, location_id=test_location.id, name='test-device-2', wireguard_ip='10.0.0.3', public_key='BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB=', internal_endpoint_host='192.168.1.101', internal_endpoint_port=51820)
        with pytest.raises(ValueError, match='Public key is already used'):
            await service.create_device(device_data2)
        await service._validate_public_key_unique(device1.public_key, test_network.id, exclude_device_id=device1.id)

@pytest.mark.asyncio
async def test_get_available_ips(test_network: WireGuardNetwork, test_location: Location, mock_session: AsyncSession, unlocked_master_password: str) -> None:
    """Test getting available IPs for a network."""
    service = DeviceService(mock_session)
    async with AsyncSessionContext(mock_session):
        await service.create_device(DeviceCreate(network_id=test_network.id, location_id=test_location.id, name='test-device-1', public_key='AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=', internal_endpoint_host='192.168.1.100', internal_endpoint_port=51820))
        await service.create_device(DeviceCreate(network_id=test_network.id, location_id=test_location.id, name='test-device-2', public_key='BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB=', internal_endpoint_host='192.168.1.101', internal_endpoint_port=51820))
        await service.create_device(DeviceCreate(network_id=test_network.id, location_id=test_location.id, name='test-device-3', public_key='CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC=', internal_endpoint_host='192.168.1.102', internal_endpoint_port=51820))
        available_ips = await service.get_available_ips(test_network.id)
        assert len(available_ips) > 0
        assert available_ips[0] == '10.0.0.4'
        assert '10.0.0.1' not in available_ips
        assert '10.0.0.2' not in available_ips
        assert '10.0.0.3' not in available_ips

@pytest.mark.asyncio
async def test_update_device_ip(test_network: WireGuardNetwork, test_location: Location, mock_session: AsyncSession, unlocked_master_password: str) -> None:
    """Test updating device IP address."""
    service = DeviceService(mock_session)
    device_data = DeviceCreate(network_id=test_network.id, location_id=test_location.id, name='test-device', public_key='AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=', internal_endpoint_host='192.168.1.100', internal_endpoint_port=51820)
    async with AsyncSessionContext(mock_session):
        device = await service.create_device(device_data)
        original_ip = device.wireguard_ip
        update_data = DeviceUpdate(wireguard_ip='10.0.0.20')
        updated_device = await service.update_device(device.id, update_data)
        assert updated_device.wireguard_ip == '10.0.0.20'
        assert updated_device.wireguard_ip != original_ip

@pytest.mark.asyncio
async def test_ip_exhaustion(test_network_small: WireGuardNetwork, mock_session: AsyncSession, unlocked_master_password: str) -> None:
    """Test behavior when network IPs are exhausted."""
    service = DeviceService(mock_session)
    from app.database.models import Location
    async with AsyncSessionContext(mock_session):
        location = Location(network_id=test_network_small.id, name='Test Location Small', description='A test location for small network', external_endpoint='192.168.1.100:51820')
        mock_session.add(location)
        await mock_session.commit()
        await mock_session.refresh(location)
    async with AsyncSessionContext(mock_session):
        device_data = DeviceCreate(network_id=test_network_small.id, location_id=location.id, name='test-device', public_key='AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=', internal_endpoint_host='192.168.1.100', internal_endpoint_port=51820)
        await service.create_device(device_data)
        devices_created = 1
        for i in range(10):
            try:
                device_data2 = DeviceCreate(network_id=test_network_small.id, location_id=location.id, name=f'test-device-{i + 2}', public_key=f"{'B' * (43 - len(str(i)))}{str(i)}=", internal_endpoint_host=f'192.168.1.{101 + i}', internal_endpoint_port=51820)
                await service.create_device(device_data2)
                devices_created += 1
            except ValueError as e:
                if 'No available IPs' in str(e):
                    break
                raise
        assert devices_created >= 1
        device_data_exhausted = DeviceCreate(network_id=test_network_small.id, location_id=location.id, name='test-device-exhausted', public_key='CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC=', internal_endpoint_host='192.168.1.200', internal_endpoint_port=51820)
        with pytest.raises(ValueError, match='No available IPs'):
            await service.create_device(device_data_exhausted)

@pytest.mark.asyncio
async def test_validate_location_belongs_to_network(test_network: WireGuardNetwork, test_location: Location, mock_session: AsyncSession) -> None:
    """Test location validation against network."""
    service = DeviceService(mock_session)
    async with AsyncSessionContext(mock_session):
        location = await service._validate_location_belongs_to_network(test_location.id, test_network.id)
        assert location.id == test_location.id
        with pytest.raises(ResourceNotFoundError, match='Location with ID'):
            await service._validate_location_belongs_to_network('invalid-location-id', test_network.id)
        with pytest.raises(ResourceNotFoundError, match='Location with ID'):
            await service._validate_location_belongs_to_network(test_location.id, 'different-network-id')

@pytest.mark.asyncio
async def test_create_device_disabled(test_network: WireGuardNetwork, test_location: Location, mock_session: AsyncSession, unlocked_master_password: str) -> None:
    """Test creating a device with enabled=false."""
    service = DeviceService(mock_session)
    device_data = DeviceCreate(network_id=test_network.id, location_id=test_location.id, name='test-device-disabled', enabled=False, public_key='KKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKK=', internal_endpoint_host='192.168.1.100', internal_endpoint_port=51820)
    async with AsyncSessionContext(mock_session):
        device = await service.create_device(device_data)
        assert device.enabled is False

@pytest.mark.asyncio
async def test_revoke_device_service(test_network: WireGuardNetwork, test_location: Location, mock_session: AsyncSession, unlocked_master_password: str) -> None:
    """Test revoking a device at service level."""
    service = DeviceService(mock_session)
    device_data = DeviceCreate(network_id=test_network.id, location_id=test_location.id, name='test-device-revoke', public_key='MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM=', internal_endpoint_host='192.168.1.100', internal_endpoint_port=51820)
    async with AsyncSessionContext(mock_session):
        device = await service.create_device(device_data)
        original_name = device.name
        assert device.enabled is True
        revoked_device = await service.revoke_device(device.id)
        assert revoked_device.enabled is False
        assert revoked_device.name == f'{original_name} (revoked)'

@pytest.mark.asyncio
async def test_revoke_device_with_api_keys(test_network: WireGuardNetwork, test_location: Location, mock_session: AsyncSession, unlocked_master_password: str) -> None:
    """Test revoking a device also disables its API keys."""
    from sqlalchemy import select
    from app.database.models import APIKey
    from app.utils.api_key import compute_api_key_fingerprint, generate_api_key
    service = DeviceService(mock_session)
    device_data = DeviceCreate(network_id=test_network.id, location_id=test_location.id, name='test-device-with-keys', public_key='NNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNN=', internal_endpoint_host='192.168.1.100', internal_endpoint_port=51820)
    async with AsyncSessionContext(mock_session):
        device = await service.create_device(device_data)
        key_value1, key_hash1 = generate_api_key()
        key_value2, key_hash2 = generate_api_key()
        key_fingerprint1 = compute_api_key_fingerprint(key_value1)
        key_fingerprint2 = compute_api_key_fingerprint(key_value2)
        api_key1 = APIKey(network_id=test_network.id, device_id=device.id, key_hash=key_hash1, key_fingerprint=key_fingerprint1, name='test-key-1', allowed_ip_ranges='10.0.0.0/24', enabled=True)
        api_key2 = APIKey(network_id=test_network.id, device_id=device.id, key_hash=key_hash2, key_fingerprint=key_fingerprint2, name='test-key-2', allowed_ip_ranges='10.0.0.0/24', enabled=True)
        mock_session.add(api_key1)
        mock_session.add(api_key2)
        await mock_session.commit()
        result = await mock_session.execute(select(APIKey).where(APIKey.device_id == device.id))
        api_keys = list(result.scalars().all())
        assert len(api_keys) == 2
        assert all((key.enabled for key in api_keys))
        await service.revoke_device(device.id)
        result = await mock_session.execute(select(APIKey).where(APIKey.device_id == device.id))
        api_keys = list(result.scalars().all())
        assert len(api_keys) == 2
        assert all((not key.enabled for key in api_keys))
        assert all(('device revoked' in key.name for key in api_keys))

@pytest.mark.asyncio
async def test_external_endpoint_uniqueness_validation_on_create(test_network: WireGuardNetwork, test_location: Location, mock_session: AsyncSession, unlocked_master_password: str) -> None:
    """Test that external endpoints must be globally unique when creating a device."""
    service = DeviceService(mock_session)
    device_data1 = DeviceCreate(network_id=test_network.id, location_id=test_location.id, name='test-device-1', public_key='OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO=', external_endpoint_host='vpn.example.com', external_endpoint_port=51820)
    async with AsyncSessionContext(mock_session):
        device1 = await service.create_device(device_data1)
        assert device1.external_endpoint_host == 'vpn.example.com'
        assert device1.external_endpoint_port == 51820
        device_data2 = DeviceCreate(network_id=test_network.id, location_id=test_location.id, name='test-device-2', public_key='PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP=', wireguard_ip='10.0.0.3', external_endpoint_host='vpn.example.com', external_endpoint_port=51820)
        with pytest.raises(ValueError, match="External endpoint 'vpn.example.com:51820' is already used"):
            await service.create_device(device_data2)

@pytest.mark.asyncio
async def test_internal_endpoint_uniqueness_validation_on_create(test_network: WireGuardNetwork, test_location: Location, mock_session: AsyncSession, unlocked_master_password: str) -> None:
    """Test that internal endpoints must be unique within a location when creating a device."""
    service = DeviceService(mock_session)
    device_data1 = DeviceCreate(network_id=test_network.id, location_id=test_location.id, name='test-device-1', public_key='QQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQ=', internal_endpoint_host='192.168.1.100', internal_endpoint_port=51820)
    async with AsyncSessionContext(mock_session):
        device1 = await service.create_device(device_data1)
        assert device1.internal_endpoint_host == '192.168.1.100'
        assert device1.internal_endpoint_port == 51820
        device_data2 = DeviceCreate(network_id=test_network.id, location_id=test_location.id, name='test-device-2', public_key='RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRR=', wireguard_ip='10.0.0.3', internal_endpoint_host='192.168.1.100', internal_endpoint_port=51820)
        with pytest.raises(ValueError, match="Internal endpoint '192.168.1.100:51820' is already used"):
            await service.create_device(device_data2)

@pytest.mark.asyncio
async def test_external_endpoint_uniqueness_validation_on_update(test_network: WireGuardNetwork, test_location: Location, mock_session: AsyncSession, unlocked_master_password: str) -> None:
    """Test that external endpoints must be globally unique when updating a device."""
    service = DeviceService(mock_session)
    async with AsyncSessionContext(mock_session):
        device_data1 = DeviceCreate(network_id=test_network.id, location_id=test_location.id, name='test-device-1', public_key='SSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSS=', external_endpoint_host='vpn1.example.com', external_endpoint_port=51820)
        device1 = await service.create_device(device_data1)
        device_data2 = DeviceCreate(network_id=test_network.id, location_id=test_location.id, name='test-device-2', public_key='TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT=', wireguard_ip='10.0.0.3', external_endpoint_host='vpn2.example.com', external_endpoint_port=51820)
        device2 = await service.create_device(device_data2)
        update_data = DeviceUpdate(external_endpoint_host='vpn1.example.com', external_endpoint_port=51820)
        with pytest.raises(ValueError, match="External endpoint 'vpn1.example.com:51820' is already used"):
            await service.update_device(device2.id, update_data)

@pytest.mark.asyncio
async def test_internal_endpoint_uniqueness_validation_on_update(test_network: WireGuardNetwork, test_location: Location, mock_session: AsyncSession, unlocked_master_password: str) -> None:
    """Test that internal endpoints must be unique within a location when updating a device."""
    service = DeviceService(mock_session)
    async with AsyncSessionContext(mock_session):
        device_data1 = DeviceCreate(network_id=test_network.id, location_id=test_location.id, name='test-device-1', public_key='UUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUU=', internal_endpoint_host='192.168.1.100', internal_endpoint_port=51820)
        device1 = await service.create_device(device_data1)
        device_data2 = DeviceCreate(network_id=test_network.id, location_id=test_location.id, name='test-device-2', public_key='VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV=', wireguard_ip='10.0.0.3', internal_endpoint_host='192.168.1.101', internal_endpoint_port=51820)
        device2 = await service.create_device(device_data2)
        update_data = DeviceUpdate(internal_endpoint_host='192.168.1.100', internal_endpoint_port=51820)
        with pytest.raises(ValueError, match="Internal endpoint '192.168.1.100:51820' is already used"):
            await service.update_device(device2.id, update_data)

@pytest.mark.asyncio
async def test_internal_endpoint_can_duplicate_across_different_locations(test_network: WireGuardNetwork, test_location: Location, mock_session: AsyncSession, unlocked_master_password: str) -> None:
    """Test that internal endpoints can be duplicated across different locations."""
    from sqlalchemy import select
    service = DeviceService(mock_session)
    location_data2 = {'network_id': test_network.id, 'name': 'test-location-2', 'external_endpoint': 'vpn.example.com:51820'}
    async with AsyncSessionContext(mock_session):
        from app.database.models import Location
        location2 = Location(**location_data2)
        mock_session.add(location2)
        await mock_session.commit()
        device_data1 = DeviceCreate(network_id=test_network.id, location_id=test_location.id, name='test-device-1', public_key='WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW=', internal_endpoint_host='192.168.1.100', internal_endpoint_port=51820)
        device1 = await service.create_device(device_data1)
        device_data2 = DeviceCreate(network_id=test_network.id, location_id=location2.id, name='test-device-2', public_key='XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX=', wireguard_ip='10.0.0.3', internal_endpoint_host='192.168.1.100', internal_endpoint_port=51820)
        device2 = await service.create_device(device_data2)
        assert device1.internal_endpoint_host == device2.internal_endpoint_host
        assert device1.internal_endpoint_port == device2.internal_endpoint_port

@pytest.mark.asyncio
async def test_external_endpoint_validation_allows_none(test_network: WireGuardNetwork, test_location: Location, mock_session: AsyncSession, unlocked_master_password: str) -> None:
    """Test that None/empty external endpoints are allowed and don't trigger uniqueness checks."""
    service = DeviceService(mock_session)
    async with AsyncSessionContext(mock_session):
        device_data1 = DeviceCreate(network_id=test_network.id, location_id=test_location.id, name='test-device-1', public_key='YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY=', internal_endpoint_host='192.168.1.110', internal_endpoint_port=51820)
        device1 = await service.create_device(device_data1)
        assert device1.external_endpoint_host is None
        assert device1.external_endpoint_port is None
        device_data2 = DeviceCreate(network_id=test_network.id, location_id=test_location.id, name='test-device-2', public_key='ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ=', wireguard_ip='10.0.0.3', internal_endpoint_host='192.168.1.111', internal_endpoint_port=51820)
        device2 = await service.create_device(device_data2)
        assert device2.external_endpoint_host is None
        assert device2.external_endpoint_port is None

@pytest.mark.asyncio
async def test_internal_endpoint_validation_allows_none(test_network: WireGuardNetwork, test_location: Location, mock_session: AsyncSession, unlocked_master_password: str) -> None:
    """Test that None/empty internal endpoints are allowed and don't trigger uniqueness checks."""
    service = DeviceService(mock_session)
    async with AsyncSessionContext(mock_session):
        device_data1 = DeviceCreate(network_id=test_network.id, location_id=test_location.id, name='test-device-1', public_key='AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=', external_endpoint_host="vpn1.example.com", external_endpoint_port=51820)
        device1 = await service.create_device(device_data1)
        assert device1.internal_endpoint_host is None
        assert device1.internal_endpoint_port is None
        device_data2 = DeviceCreate(network_id=test_network.id, location_id=test_location.id, name='test-device-2', public_key='BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB=', wireguard_ip='10.0.0.3', external_endpoint_host="vpn2.example.com", external_endpoint_port=51820)
        device2 = await service.create_device(device_data2)
        assert device2.internal_endpoint_host is None
        assert device2.internal_endpoint_port is None

@pytest.mark.asyncio
async def test_can_update_device_to_same_external_endpoint(test_network: WireGuardNetwork, test_location: Location, mock_session: AsyncSession, unlocked_master_password: str) -> None:
    """Test that a device can be updated while keeping the same external endpoint."""
    service = DeviceService(mock_session)
    async with AsyncSessionContext(mock_session):
        device_data = DeviceCreate(network_id=test_network.id, location_id=test_location.id, name='test-device', public_key='CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC=', external_endpoint_host='vpn.example.com', external_endpoint_port=51820)
        device = await service.create_device(device_data)
        update_data = DeviceUpdate(name='updated-name', external_endpoint_host='vpn.example.com', external_endpoint_port=51820)
        updated_device = await service.update_device(device.id, update_data)
        assert updated_device.name == 'updated-name'
        assert updated_device.external_endpoint_host == 'vpn.example.com'
        assert updated_device.external_endpoint_port == 51820

@pytest.mark.asyncio
async def test_can_update_device_to_same_internal_endpoint(test_network: WireGuardNetwork, test_location: Location, mock_session: AsyncSession, unlocked_master_password: str) -> None:
    """Test that a device can be updated while keeping the same internal endpoint."""
    service = DeviceService(mock_session)
    async with AsyncSessionContext(mock_session):
        device_data = DeviceCreate(network_id=test_network.id, location_id=test_location.id, name='test-device', public_key='DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD=', internal_endpoint_host='192.168.1.100', internal_endpoint_port=51820)
        device = await service.create_device(device_data)
        update_data = DeviceUpdate(name='updated-name', internal_endpoint_host='192.168.1.100', internal_endpoint_port=51820)
        updated_device = await service.update_device(device.id, update_data)
        assert updated_device.name == 'updated-name'
        assert updated_device.internal_endpoint_host == '192.168.1.100'
        assert updated_device.internal_endpoint_port == 51820