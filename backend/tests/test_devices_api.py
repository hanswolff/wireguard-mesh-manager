"""Tests for device API endpoints."""
from __future__ import annotations
from typing import TYPE_CHECKING
import pytest
from app.main import app
from app.utils.key_management import generate_wireguard_keypair
from tests.conftest import AsyncSessionContext, get_test_client
pytestmark = pytest.mark.usefixtures('unlocked_master_password')
if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.database.models import Location, WireGuardNetwork

@pytest.mark.asyncio
async def test_create_device_auto_ip_allocation(test_network: WireGuardNetwork, test_location: Location, mock_session: AsyncSession) -> None:
    """Test creating a device with automatic IP allocation."""
    client = get_test_client(app, mock_session, authenticated=True)
    private_key, public_key = generate_wireguard_keypair()
    device_data = {'network_id': test_network.id, 'location_id': test_location.id, 'name': 'test-device', 'description': 'Test device for API testing', 'public_key': public_key, 'private_key': private_key, 'internal_endpoint_host': '192.168.1.100', 'internal_endpoint_port': 51820}
    async with AsyncSessionContext(mock_session):
        response = client.post('/api/devices/', json=device_data)
        if response.status_code != 201:
            print(f'Response: {response.status_code}')
            print(f'Response body: {response.text}')
        assert response.status_code == 201
        data = response.json()
        assert data['name'] == 'test-device'
        assert data['network_id'] == test_network.id
        assert data['location_id'] == test_location.id
        assert data['wireguard_ip'] == '10.0.0.1'
        assert data['enabled'] is True
        assert 'id' in data
        assert 'created_at' in data
        assert 'updated_at' in data

@pytest.mark.asyncio
async def test_create_device_with_specific_ip(test_network: WireGuardNetwork, test_location: Location, mock_session: AsyncSession) -> None:
    """Test creating a device with a specific IP address."""
    client = get_test_client(app, mock_session, authenticated=True)
    private_key, public_key = generate_wireguard_keypair()
    device_data = {'network_id': test_network.id, 'location_id': test_location.id, 'name': 'test-device-specific-ip', 'wireguard_ip': '10.0.0.50', 'internal_endpoint_host': '192.168.1.100', 'internal_endpoint_port': 51820, 'public_key': public_key, 'private_key': private_key}
    async with AsyncSessionContext(mock_session):
        response = client.post('/api/devices/', json=device_data)
        assert response.status_code == 201
        data = response.json()
        assert data['wireguard_ip'] == '10.0.0.50'

@pytest.mark.asyncio
async def test_create_device_invalid_ip(test_network: WireGuardNetwork, test_location: Location, mock_session: AsyncSession) -> None:
    """Test creating a device with invalid IP address."""
    client = get_test_client(app, mock_session)
    private_key, public_key = generate_wireguard_keypair()
    device_data = {'network_id': test_network.id, 'location_id': test_location.id, 'name': 'test-device-invalid-ip', 'wireguard_ip': '192.168.1.100', 'public_key': public_key, 'private_key': private_key, 'internal_endpoint_host': '192.168.1.100', 'internal_endpoint_port': 51820}
    async with AsyncSessionContext(mock_session):
        response = client.post('/api/devices/', json=device_data)
        assert response.status_code == 422
        data = response.json()
        assert data['error'] == 'validation_error'
        assert any(('not within network CIDR' in detail['msg'] for detail in data.get('details', [])))

@pytest.mark.asyncio
async def test_create_device_duplicate_ip(test_network: WireGuardNetwork, test_location: Location, mock_session: AsyncSession) -> None:
    """Test creating a device with duplicate IP address."""
    client = get_test_client(app, mock_session, authenticated=True)
    private_key1, public_key1 = generate_wireguard_keypair()
    private_key2, public_key2 = generate_wireguard_keypair()
    device_data1 = {'network_id': test_network.id, 'location_id': test_location.id, 'name': 'test-device-1', 'wireguard_ip': '10.0.0.100', 'public_key': public_key1, 'private_key': private_key1, 'internal_endpoint_host': '192.168.1.101', 'internal_endpoint_port': 51821}
    device_data2 = {'network_id': test_network.id, 'location_id': test_location.id, 'name': 'test-device-2', 'wireguard_ip': '10.0.0.100', 'public_key': public_key2, 'private_key': private_key2, 'internal_endpoint_host': '192.168.1.102', 'internal_endpoint_port': 51822}
    async with AsyncSessionContext(mock_session):
        response1 = client.post('/api/devices/', json=device_data1)
        assert response1.status_code == 201
        response2 = client.post('/api/devices/', json=device_data2)
        assert response2.status_code == 422
        data = response2.json()
        assert data['error'] == 'validation_error'
        assert any(('already allocated' in detail['msg'] for detail in data.get('details', [])))

@pytest.mark.asyncio
async def test_get_devices_by_network(test_network: WireGuardNetwork, test_location: Location, mock_session: AsyncSession) -> None:
    """Test getting devices by network ID."""
    client = get_test_client(app, mock_session)
    async with AsyncSessionContext(mock_session):
        for i in range(3):
            private_key, public_key = generate_wireguard_keypair()
            device_data = {'network_id': test_network.id, 'location_id': test_location.id, 'name': f'test-device-{i + 1}', 'public_key': public_key, 'private_key': private_key, 'internal_endpoint_host': f'192.168.1.{10 + i}', 'internal_endpoint_port': 51820 + i}
            client.post('/api/devices/', json=device_data)
        response = client.get(f'/api/devices/network/{test_network.id}')
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert all((device['network_id'] == test_network.id for device in data))

@pytest.mark.asyncio
async def test_get_available_ips(test_network: WireGuardNetwork, test_location: Location, mock_session: AsyncSession) -> None:
    """Test getting available IPs for a network."""
    client = get_test_client(app, mock_session)
    async with AsyncSessionContext(mock_session):
        for i in range(3):
            private_key, public_key = generate_wireguard_keypair()
            device_data = {'network_id': test_network.id, 'location_id': test_location.id, 'name': f'test-device-{i + 1}', 'public_key': public_key, 'private_key': private_key, 'internal_endpoint_host': f'192.168.1.{20 + i}', 'internal_endpoint_port': 51820 + i}
            client.post('/api/devices/', json=device_data)
        response = client.get(f'/api/devices/network/{test_network.id}/available-ips')
        assert response.status_code == 200
        data = response.json()
        assert 'allocated_ip' in data
        assert 'available_ips' in data
        assert len(data['available_ips']) > 0
        assert '10.0.0.5' in data['available_ips']

@pytest.mark.asyncio
async def test_update_device_ip(test_network: WireGuardNetwork, test_location: Location, mock_session: AsyncSession) -> None:
    """Test updating a device's IP address."""
    client = get_test_client(app, mock_session)
    private_key, public_key = generate_wireguard_keypair()
    device_data = {'network_id': test_network.id, 'location_id': test_location.id, 'name': 'test-device', 'public_key': public_key, 'private_key': private_key, 'internal_endpoint_host': '192.168.1.100', 'internal_endpoint_port': 51820}
    update_data = {'wireguard_ip': '10.0.0.150'}
    async with AsyncSessionContext(mock_session):
        response = client.post('/api/devices/', json=device_data)
        device_id = response.json()['id']
        response = client.put(f'/api/devices/{device_id}', json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data['wireguard_ip'] == '10.0.0.150'

@pytest.mark.asyncio
async def test_invalid_public_key_format(test_network: WireGuardNetwork, test_location: Location, mock_session: AsyncSession) -> None:
    """Test creating device with invalid public key format."""
    client = get_test_client(app, mock_session, authenticated=True)
    device_data = {'network_id': test_network.id, 'location_id': test_location.id, 'name': 'test-device', 'public_key': 'invalid-key-format-not-base64', 'private_key': 'CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC=', 'internal_endpoint_host': '192.168.1.100', 'internal_endpoint_port': 51820}
    async with AsyncSessionContext(mock_session):
        response = client.post('/api/devices/', json=device_data)
        assert response.status_code == 422

@pytest.mark.asyncio
async def test_invalid_preshared_key_format(test_network: WireGuardNetwork, test_location: Location, mock_session: AsyncSession) -> None:
    """Test creating device with invalid preshared key format."""
    client = get_test_client(app, mock_session)
    private_key, public_key = generate_wireguard_keypair()
    device_data = {'network_id': test_network.id, 'location_id': test_location.id, 'name': 'test-device', 'public_key': public_key, 'private_key': private_key, 'preshared_key': 'invalid-psk-format', 'internal_endpoint_host': '192.168.1.100', 'internal_endpoint_port': 51820}
    async with AsyncSessionContext(mock_session):
        response = client.post('/api/devices/', json=device_data)
        assert response.status_code == 422

@pytest.mark.asyncio
async def test_delete_device(test_network: WireGuardNetwork, test_location: Location, mock_session: AsyncSession) -> None:
    """Test deleting a device."""
    client = get_test_client(app, mock_session)
    private_key, public_key = generate_wireguard_keypair()
    device_data = {'network_id': test_network.id, 'location_id': test_location.id, 'name': 'test-device-to-delete', 'public_key': public_key, 'private_key': private_key, 'internal_endpoint_host': '192.168.1.100', 'internal_endpoint_port': 51820}
    async with AsyncSessionContext(mock_session):
        response = client.post('/api/devices/', json=device_data)
        assert response.status_code == 201
        device_id = response.json()['id']
        response = client.delete(f'/api/devices/{device_id}')
        assert response.status_code == 200
        assert 'deleted successfully' in response.json()['message']
        response = client.get(f'/api/devices/{device_id}')
        assert response.status_code == 404

@pytest.mark.asyncio
async def test_create_device_disabled(test_network: WireGuardNetwork, test_location: Location, mock_session: AsyncSession) -> None:
    """Test creating a device with enabled=false."""
    client = get_test_client(app, mock_session)
    private_key, public_key = generate_wireguard_keypair()
    device_data = {'network_id': test_network.id, 'location_id': test_location.id, 'name': 'test-device-disabled', 'enabled': False, 'public_key': public_key, 'private_key': private_key, 'internal_endpoint_host': '192.168.1.100', 'internal_endpoint_port': 51820}
    async with AsyncSessionContext(mock_session):
        response = client.post('/api/devices/', json=device_data)
        assert response.status_code == 201
        data = response.json()
        assert data['enabled'] is False

@pytest.mark.asyncio
async def test_update_device_enable_disable(test_network: WireGuardNetwork, test_location: Location, mock_session: AsyncSession) -> None:
    """Test enabling and disabling a device."""
    client = get_test_client(app, mock_session)
    private_key, public_key = generate_wireguard_keypair()
    device_data = {'network_id': test_network.id, 'location_id': test_location.id, 'name': 'test-device-toggle', 'public_key': public_key, 'private_key': private_key, 'internal_endpoint_host': '192.168.1.100', 'internal_endpoint_port': 51820}
    async with AsyncSessionContext(mock_session):
        response = client.post('/api/devices/', json=device_data)
        assert response.status_code == 201
        device_id = response.json()['id']
        assert response.json()['enabled'] is True
        response = client.put(f'/api/devices/{device_id}', json={'enabled': False})
        assert response.status_code == 200
        assert response.json()['enabled'] is False
        response = client.put(f'/api/devices/{device_id}', json={'enabled': True})
        assert response.status_code == 200
        assert response.json()['enabled'] is True

@pytest.mark.skip(reason='/revoke endpoint not implemented')
@pytest.mark.asyncio
async def test_revoke_device(test_network: WireGuardNetwork, test_location: Location, mock_session: AsyncSession, unlocked_master_password: str) -> None:
    """Test revoking a device (emergency lockdown)."""
    client = get_test_client(app, mock_session)
    private_key, public_key = generate_wireguard_keypair()
    device_data = {'network_id': test_network.id, 'location_id': test_location.id, 'name': 'test-device-revoke', 'public_key': public_key, 'private_key': private_key, 'internal_endpoint_host': '192.168.1.100', 'internal_endpoint_port': 51820}
    async with AsyncSessionContext(mock_session):
        response = client.post('/api/devices/', json=device_data)
        assert response.status_code == 201
        device_id = response.json()['id']
        original_name = response.json()['name']
        response = client.post(f'/api/devices/{device_id}/revoke')
        assert response.status_code == 200
        assert 'revoked successfully' in response.json()['message']
        response = client.get(f'/api/devices/{device_id}')
        assert response.status_code == 200
        data = response.json()
        assert data['enabled'] is False
        assert data['name'] == f'{original_name} (revoked)'

@pytest.mark.asyncio
async def test_update_device_endpoints(test_network: WireGuardNetwork, test_location: Location, mock_session: AsyncSession) -> None:
    """Test updating a device's external and internal endpoints."""
    client = get_test_client(app, mock_session, authenticated=True)
    private_key, public_key = generate_wireguard_keypair()
    device_data = {'network_id': test_network.id, 'location_id': test_location.id, 'name': 'test-device-endpoints', 'public_key': public_key, 'private_key': private_key, 'internal_endpoint_host': '192.168.1.100', 'internal_endpoint_port': 51820}
    async with AsyncSessionContext(mock_session):
        response = client.post('/api/devices/', json=device_data)
        assert response.status_code == 201
        device_id = response.json()['id']
        assert response.json()['external_endpoint_host'] is None
        assert response.json()['external_endpoint_port'] is None
        assert response.json()['internal_endpoint_host'] == '192.168.1.100'
        assert response.json()['internal_endpoint_port'] == 51820
        response = client.put(f'/api/devices/{device_id}', json={'external_endpoint_host': 'example.com', 'external_endpoint_port': 51820})
        assert response.status_code == 200
        data = response.json()
        assert data['external_endpoint_host'] == 'example.com'
        assert data['external_endpoint_port'] == 51820
        assert data['internal_endpoint_host'] == '192.168.1.100'
        assert data['internal_endpoint_port'] == 51820
        response = client.put(f'/api/devices/{device_id}', json={'external_endpoint_host': 'myserver.com', 'external_endpoint_port': 51820, 'internal_endpoint_host': '192.168.1.100', 'internal_endpoint_port': 51820})
        assert response.status_code == 200
        data = response.json()
        assert data['external_endpoint_host'] == 'myserver.com'
        assert data['external_endpoint_port'] == 51820
        assert data['internal_endpoint_host'] == '192.168.1.100'
        assert data['internal_endpoint_port'] == 51820
        response = client.get(f'/api/devices/{device_id}')
        assert response.status_code == 200
        data = response.json()
        assert data['external_endpoint_host'] == 'myserver.com'
        assert data['external_endpoint_port'] == 51820
        assert data['internal_endpoint_host'] == '192.168.1.100'
        assert data['internal_endpoint_port'] == 51820

@pytest.mark.asyncio
async def test_list_devices_filter_by_network(test_network: WireGuardNetwork, test_location: Location, mock_session: AsyncSession) -> None:
    """Test listing devices filtered by network ID."""
    client = get_test_client(app, mock_session)
    async with AsyncSessionContext(mock_session):
        network_response_2 = client.post('/api/networks/', json={'name': 'Second Network', 'description': 'A second network', 'network_cidr': '10.0.1.0/24'})
        assert network_response_2.status_code == 201
        network_id_2 = network_response_2.json()['id']
        location_response_2 = client.post('/api/locations/', json={'network_id': network_id_2, 'name': 'Location in Network 2'})
        assert location_response_2.status_code == 201
        location_id_2 = location_response_2.json()['id']
        private_key1, public_key1 = generate_wireguard_keypair()
        device_response_1 = client.post('/api/devices/', json={'network_id': test_network.id, 'location_id': test_location.id, 'name': 'device-in-network-1', 'public_key': public_key1, 'private_key': private_key1, 'internal_endpoint_host': '192.168.1.103', 'internal_endpoint_port': 51823})
        assert device_response_1.status_code == 201
        device_id_1 = device_response_1.json()['id']
        private_key2, public_key2 = generate_wireguard_keypair()
        device_response_2 = client.post('/api/devices/', json={'network_id': network_id_2, 'location_id': location_id_2, 'name': 'device-in-network-2', 'public_key': public_key2, 'private_key': private_key2, 'internal_endpoint_host': '192.168.1.104', 'internal_endpoint_port': 51824})
        assert device_response_2.status_code == 201
        device_id_2 = device_response_2.json()['id']
        all_response = client.get('/api/devices/')
        assert all_response.status_code == 200
        all_devices = all_response.json()
        assert len(all_devices) == 2
        network_1_response = client.get(f'/api/devices/?network_id={test_network.id}')
        assert network_1_response.status_code == 200
        network_1_devices = network_1_response.json()
        assert len(network_1_devices) == 1
        assert network_1_devices[0]['id'] == device_id_1
        assert network_1_devices[0]['network_id'] == test_network.id
        network_2_response = client.get(f'/api/devices/?network_id={network_id_2}')
        assert network_2_response.status_code == 200
        network_2_devices = network_2_response.json()
        assert len(network_2_devices) == 1
        assert network_2_devices[0]['id'] == device_id_2
        assert network_2_devices[0]['network_id'] == network_id_2
        invalid_response = client.get('/api/devices/?network_id=invalid-uuid')
        assert invalid_response.status_code == 200
        assert invalid_response.json() == []

@pytest.mark.asyncio
async def test_revoke_nonexistent_device(mock_session: AsyncSession) -> None:
    """Test revoking a non-existent device."""
    client = get_test_client(app, mock_session)
    async with AsyncSessionContext(mock_session):
        response = client.post('/api/devices/non-existent-id/revoke')
        assert response.status_code == 404