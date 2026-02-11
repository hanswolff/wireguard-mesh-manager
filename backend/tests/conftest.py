"""Test configuration and fixtures."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.models import Base, Device, Location, WireGuardNetwork
from app.main import app
from app.services.master_session import master_session_manager


def generate_test_wireguard_ip() -> str:
    """Generate a unique test WireGuard IP address."""
    # Use a range that won't conflict with common setups
    last_octet = (int(uuid4().hex[:8], 16) % 200) + 50  # Range 50-249
    return f"10.0.0.{last_octet}"


def generate_test_public_key() -> str:
    """Generate a unique test public key."""
    # Generate a valid base64 encoded string of length 44
    unique_id = uuid4().hex + uuid4().hex
    # Pad with '=' to make it valid base64 length if needed
    return (unique_id[:44] + "=" * 44)[:44]


@pytest_asyncio.fixture
async def db_session():
    """Create a database session for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = tmp_file.name

    database_url = f"sqlite+aiosqlite:///{db_path}"

    engine = create_async_engine(
        database_url,
        echo=False,
        future=True,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    test_session_local = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with test_session_local() as session:
        yield session

    await engine.dispose()
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def unique_network_name():
    """Generate a unique network name for testing."""
    return f"Test Network {uuid4().hex[:8]}"


@pytest.fixture
def sample_network_data(unique_network_name):
    """Sample network data for testing."""
    return {
        "name": unique_network_name,
        "description": "A test network",
        "network_cidr": "10.0.0.0/24",
        "private_key_encrypted": "encrypted_private_key",
        "public_key": "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=",
    }


@pytest_asyncio.fixture
async def async_client(db_session):
    """Create an async HTTP client for testing."""
    from app.database.connection import get_db
    from app.routers.api_keys import get_api_key_service
    from app.routers.devices import get_device_service
    from app.routers.health import get_metrics_service
    from app.routers.key_rotation import get_key_rotation_service
    from app.routers.locations import get_location_service
    from app.routers.networks import get_network_service
    from app.routers.devices import get_device_config_service
    from app.routers.utils import get_audit_service
    from app.services.api_key import APIKeyService
    from app.services.audit import AuditService
    from app.services.device_config import DeviceConfigService
    from app.services.devices import DeviceService
    from app.services.key_rotation import KeyRotationService
    from app.services.locations import LocationService
    from app.services.metrics import MetricsService
    from app.services.networks import NetworkService

    # Override the dependency to use test database
    async def override_get_db():
        yield db_session

    # Override audit service to use test database
    def override_get_audit_service():
        return AuditService(db_session)

    # Override all service dependencies to use test database directly
    def override_get_api_key_service():
        return APIKeyService(db_session)

    def override_get_device_service():
        return DeviceService(db_session)

    def override_get_network_service():
        return NetworkService(db_session)

    def override_get_location_service():
        return LocationService(db_session)

    def override_get_key_rotation_service():
        return KeyRotationService(db_session)

    def override_get_metrics_service():
        return MetricsService(app.state.metrics_middleware)

    def override_get_device_config_service():
        return DeviceConfigService(db_session)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_audit_service] = override_get_audit_service
    app.dependency_overrides[get_api_key_service] = override_get_api_key_service
    app.dependency_overrides[get_device_service] = override_get_device_service
    app.dependency_overrides[get_network_service] = override_get_network_service
    app.dependency_overrides[get_location_service] = override_get_location_service
    app.dependency_overrides[get_key_rotation_service] = (
        override_get_key_rotation_service
    )
    app.dependency_overrides[get_metrics_service] = override_get_metrics_service
    app.dependency_overrides[get_device_config_service] = override_get_device_config_service
    import httpx

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        yield client

    # Clean up dependency override
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def master_session_token() -> str:
    """Create a master session token for admin endpoints."""
    token, _session = master_session_manager.create_session(
        ip_address="127.0.0.1",
    )
    return token


@pytest_asyncio.fixture
async def test_network(db_session, unique_network_name):
    """Create a test network for testing."""
    from app.utils.key_management import (
        generate_wireguard_private_key,
        generate_device_dek,
        encrypt_private_key_with_dek,
    )

    # Generate proper encrypted key for testing (mesh topology)
    private_key = generate_wireguard_private_key()
    device_dek = generate_device_dek()
    private_key_encrypted = encrypt_private_key_with_dek(private_key, device_dek)

    network = WireGuardNetwork(
        name=unique_network_name,
        description="A test network",
        network_cidr="10.0.0.0/24",
        private_key_encrypted=private_key_encrypted,
        public_key=generate_test_public_key(),
    )
    db_session.add(network)
    await db_session.commit()
    await db_session.refresh(network)
    return network


@pytest_asyncio.fixture
async def test_network_small(db_session, unique_network_name):
    """Create a small test network for testing IP exhaustion."""
    network = WireGuardNetwork(
        name=f"{unique_network_name}_small",
        description="A small test network",
        network_cidr="10.0.0.0/30",  # Only 2 usable IPs
        private_key_encrypted="encrypted_private_key",
        public_key=generate_test_public_key(),
    )
    db_session.add(network)
    await db_session.commit()
    await db_session.refresh(network)
    return network


@pytest_asyncio.fixture
async def test_location(db_session, test_network):
    """Create a test location for testing."""
    location = Location(
        network_id=test_network.id,
        name="Test Location",
        description="A test location",
        external_endpoint="192.168.1.100",
    )
    db_session.add(location)
    await db_session.commit()
    await db_session.refresh(location)
    return location


@pytest_asyncio.fixture
async def test_location_small(db_session, test_network_small):
    """Create a test location for the small network."""
    location = Location(
        network_id=test_network_small.id,
        name="Small Network Location",
        description="A test location for small network",
        external_endpoint="192.168.1.100",
    )
    db_session.add(location)
    await db_session.commit()
    await db_session.refresh(location)
    return location


@pytest_asyncio.fixture
async def test_device(db_session, test_network, test_location, unlocked_master_password):
    """Create a test device for testing."""
    from app.utils.key_management import (
        generate_wireguard_private_key,
        generate_device_dek,
        encrypt_private_key_with_dek,
        encrypt_device_dek_with_master,
        derive_wireguard_public_key,
    )

    test_password = "test_master_password_123"  # pragma: allowlist secret

    # Generate proper keys for testing
    private_key = generate_wireguard_private_key()
    public_key = derive_wireguard_public_key(private_key)
    device_dek = generate_device_dek()

    # Encrypt keys properly
    private_key_encrypted = encrypt_private_key_with_dek(private_key, device_dek)
    device_dek_encrypted_master = encrypt_device_dek_with_master(device_dek, test_password)

    device = Device(
        network_id=test_network.id,
        location_id=test_location.id,
        name="Test Device",
        description="A test device",
        wireguard_ip=generate_test_wireguard_ip(),
        private_key_encrypted=private_key_encrypted,
        device_dek_encrypted_master=device_dek_encrypted_master,
        public_key=public_key,
    )
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)
    return device


@pytest_asyncio.fixture
async def sample_network(test_network):
    """Create a sample network for testing (alias for test_network)."""
    return test_network


@pytest_asyncio.fixture
async def sample_location(test_location):
    """Create a sample location for testing (alias for test_location)."""
    return test_location


@pytest_asyncio.fixture
async def sample_device(test_device):
    """Create a sample device for testing (alias for test_device)."""
    return test_device


@pytest_asyncio.fixture
async def mock_session(db_session):
    """Mock session for testing (alias for db_session)."""
    return db_session


@pytest_asyncio.fixture
async def client(async_client):
    """Provide a conventional fixture name for async HTTP client usage."""
    return async_client


class AsyncSessionContext:
    """Context manager for async session operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            await self.session.commit()
        else:
            await self.session.rollback()


def get_test_client(app_instance, db_session=None, authenticated=False):
    """Create a TestClient with optional database session override."""
    if db_session is not None:
        from app.database.connection import get_db

        # Override the dependency to use test database
        async def override_get_db():
            yield db_session

        app_instance.dependency_overrides[get_db] = override_get_db

    headers = None
    if authenticated:
        token, _session = master_session_manager.create_session()
        headers = {"Authorization": f"Master {token}"}

    return TestClient(app_instance, headers=headers)


@pytest.fixture(autouse=True)
def disable_csrf_protection(request):
    """Disable CSRF protection for most tests while allowing CSRF-focused tests."""
    if "test_csrf" in request.node.nodeid:
        yield
        return
    with patch("app.middleware.csrf.settings.csrf_protection_enabled", False):
        yield


@pytest.fixture(autouse=True)
def disable_rate_limiting(request):
    """Disable rate limiting for most tests to avoid cross-test throttling."""
    if "rate_limit" in request.node.nodeid or "rate_limiting" in request.node.nodeid:
        yield
        return
    with patch(
        "app.middleware.rate_limit.RateLimitMiddleware._should_skip_rate_limit",
        return_value=True,
    ):
        yield


@pytest.fixture(autouse=True)
async def override_db_dependency(db_session):
    """Ensure all app routes use the per-test database session by default."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app import database
    from app.database.connection import get_db

    async def override_get_db():
        yield db_session

    original_session_local = database.connection.AsyncSessionLocal
    database.connection.AsyncSessionLocal = async_sessionmaker(
        db_session.bind, class_=AsyncSession, expire_on_commit=False
    )

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)
    database.connection.AsyncSessionLocal = original_session_local


@pytest.fixture(autouse=True)
def bypass_auth_middleware(request):
    """Bypass authentication middleware for most tests while allowing auth-focused tests."""
    if "auth" in request.node.nodeid:
        app.state.bypass_auth = False
        yield
        return

    app.state.bypass_auth = True
    yield
    app.state.bypass_auth = False


@pytest.fixture
def cleanup_dependencies():
    """Fixture to clean up dependency overrides after test."""
    yield
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_api_key(test_device: Device, db_session: AsyncSession):
    """Create a test API key."""
    from app.schemas.devices import APIKeyCreate
    from app.services.api_key import APIKeyService
    from app.utils.api_key import compute_api_key_fingerprint, generate_api_key

    service = APIKeyService(db_session)
    key_value, key_hash = generate_api_key()

    api_key_data = APIKeyCreate(
        name="Test API Key",
        device_id=test_device.id,
        allowed_ip_ranges="192.168.1.0/24",
        enabled=True,
    )

    key_fingerprint = compute_api_key_fingerprint(key_value)
    api_key = await service.create_api_key(api_key_data, key_hash, key_fingerprint)

    # Return a dict representation for testing
    return {
        "id": api_key.id,
        "name": api_key.name,
        "device_id": api_key.device_id,
        "network_id": api_key.network_id,
        "allowed_ip_ranges": api_key.allowed_ip_ranges,
        "enabled": api_key.enabled,
        "key_value": key_value,
    }


@pytest.fixture
def unlocked_master_password():
    """Provide an unlocked master password cache for testing."""
    from app.services.master_password import master_password_cache

    # Use a fixed test password for consistency  # pragma: allowlist secret
    test_password = "test_master_password_123"  # pragma: allowlist secret
    master_password_cache.unlock(test_password)

    yield test_password

    # Lock the cache after the test
    master_password_cache.lock()
