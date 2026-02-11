"""Test for the new audit events API endpoint."""

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import WireGuardNetwork
from app.services.audit import AuditService


@pytest_asyncio.fixture
async def audit_service(db_session: AsyncSession) -> AuditService:
    """Create audit service fixture."""
    return AuditService(db_session)


@pytest.mark.asyncio
async def test_list_audit_events_basic(
    async_client: AsyncClient,
    test_network: WireGuardNetwork,
    audit_service: AuditService,
):
    """Test basic audit events listing functionality."""
    # Create some test audit events
    await audit_service.log_admin_action(
        network_id=str(test_network.id),
        admin_actor="test-user",
        action="NETWORK_CREATED",
        resource_type="network",
    )

    await audit_service.log_admin_action(
        network_id=str(test_network.id),
        admin_actor="test-user",
        action="DEVICE_ADDED",
        resource_type="device",
        resource_id="test-device-id",
    )

    # Test the events endpoint
    response = await async_client.get("/api/audit/events?")
    assert response.status_code == 200

    data = response.json()
    assert "events" in data
    assert "pagination" in data
    assert "filters_applied" in data

    # Check pagination structure
    pagination = data["pagination"]
    assert "page" in pagination
    assert "page_size" in pagination
    assert "total_count" in pagination
    assert "total_pages" in pagination
    assert "has_next" in pagination
    assert "has_previous" in pagination

    # Check events structure
    events = data["events"]
    assert len(events) >= 2  # At least the events we created

    # Check event structure
    event = events[0]
    assert "id" in event
    assert "network_id" in event
    assert "actor" in event
    assert "action" in event
    assert "resource_type" in event
    assert "created_at" in event
    assert "details" in event

    # Check that actions we created are present
    actions = [event["action"] for event in events]
    assert "NETWORK_CREATED" in actions
    assert "DEVICE_ADDED" in actions


@pytest.mark.asyncio
async def test_list_audit_events_with_filters(
    async_client: AsyncClient,
    test_network: WireGuardNetwork,
    audit_service: AuditService,
):
    """Test audit events listing with filters applied."""
    # Create test events with different actions
    await audit_service.log_admin_action(
        network_id=str(test_network.id),
        admin_actor="user1",
        action="CREATE",
        resource_type="network",
    )

    await audit_service.log_admin_action(
        network_id=str(test_network.id),
        admin_actor="user2",
        action="DELETE",
        resource_type="device",
    )

    # Test filtering by actor
    response = await async_client.get("/api/audit/events?actor=user1")
    assert response.status_code == 200
    data = response.json()
    assert all(event["actor"] == "user1" for event in data["events"])

    # Test filtering by action
    response = await async_client.get("/api/audit/events?action=DELETE")
    assert response.status_code == 200
    data = response.json()
    assert all(event["action"] == "DELETE" for event in data["events"])

    # Test filtering by resource_type
    response = await async_client.get("/api/audit/events?resource_type=network")
    assert response.status_code == 200
    data = response.json()
    assert all(event["resource_type"] == "network" for event in data["events"])


@pytest.mark.asyncio
async def test_list_audit_events_pagination(
    async_client: AsyncClient,
    test_network: WireGuardNetwork,
    audit_service: AuditService,
):
    """Test audit events listing pagination."""
    # Create several test events
    for i in range(5):
        await audit_service.log_admin_action(
            network_id=str(test_network.id),
            admin_actor="test-user",
            action=f"ACTION_{i}",
            resource_type="test",
        )

    # Test first page with page_size=2
    response = await async_client.get("/api/audit/events?page=1&page_size=2")
    assert response.status_code == 200
    data = response.json()

    assert len(data["events"]) == 2
    assert data["pagination"]["page"] == 1
    assert data["pagination"]["page_size"] == 2
    assert data["pagination"]["total_count"] >= 5
    assert data["pagination"]["has_next"] is True
    assert data["pagination"]["has_previous"] is False

    # Test second page
    response = await async_client.get("/api/audit/events?page=2&page_size=2")
    assert response.status_code == 200
    data = response.json()

    assert len(data["events"]) == 2
    assert data["pagination"]["page"] == 2
    assert data["pagination"]["has_previous"] is True


@pytest.mark.asyncio
async def test_list_audit_events_with_details(
    async_client: AsyncClient,
    test_network: WireGuardNetwork,
    audit_service: AuditService,
):
    """Test audit events listing with details included."""
    test_changes = {"test_key": "test_value", "nested": {"data": "value"}}

    await audit_service.log_admin_action(
        network_id=str(test_network.id),
        admin_actor="test-user",
        action="UPDATE",
        resource_type="device",
        resource_name="test-device",
        changes=test_changes,
    )

    # Test without details (default)
    response = await async_client.get("/api/audit/events?include_details=false")
    assert response.status_code == 200
    data = response.json()
    event = next(e for e in data["events"] if e["action"] == "UPDATE")
    assert event["details"] is None

    # Test with details
    response = await async_client.get("/api/audit/events?include_details=true")
    assert response.status_code == 200
    data = response.json()
    event = next(e for e in data["events"] if e["action"] == "UPDATE")
    assert event["details"] is not None
    assert event["details"]["resource_name"] == "test-device"
    assert event["details"]["changes"]["test_key"] == "test_value"


@pytest.mark.asyncio
async def test_list_audit_events_date_filter(
    async_client: AsyncClient,
    test_network: WireGuardNetwork,
    audit_service: AuditService,
):
    """Test audit events listing with date range filtering."""
    # Create an event at a specific time
    now = datetime.now(UTC)
    await audit_service.log_admin_action(
        network_id=str(test_network.id),
        admin_actor="test-user",
        action="DATE_TEST",
        resource_type="test",
    )

    # Test filtering with date range that should include the event
    start_date = now.replace(hour=0, minute=0, second=0, microsecond=0).strftime(
        "%Y-%m-%dT%H:%M:%S.%fZ"
    )
    end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999).strftime(
        "%Y-%m-%dT%H:%M:%S.%fZ"
    )

    response = await async_client.get(
        f"/api/audit/events?start_date={start_date}&end_date={end_date}"
    )
    assert response.status_code == 200
    data = response.json()

    date_test_events = [e for e in data["events"] if e["action"] == "DATE_TEST"]
    assert len(date_test_events) >= 1


@pytest.mark.asyncio
async def test_list_audit_events_network_filter(
    async_client: AsyncClient,
    test_network: WireGuardNetwork,
    audit_service: AuditService,
):
    """Test audit events listing filtered by network ID."""
    # Create an event for the test network
    await audit_service.log_admin_action(
        network_id=str(test_network.id),
        admin_actor="test-user",
        action="NETWORK_TEST",
        resource_type="network",
    )

    # Test filtering by the specific network ID
    response = await async_client.get(f"/api/audit/events?network_id={test_network.id}")
    assert response.status_code == 200
    data = response.json()

    network_events = [
        e for e in data["events"] if e["network_id"] == str(test_network.id)
    ]
    assert len(network_events) >= 1
    assert any(e["action"] == "NETWORK_TEST" for e in network_events)

    # Check that network_name is included when there's a network relationship
    network_test_event = next(
        e for e in network_events if e["action"] == "NETWORK_TEST"
    )
    assert network_test_event["network_name"] == test_network.name


@pytest.mark.asyncio
async def test_list_audit_events_empty_result(async_client: AsyncClient):
    """Test audit events listing with filters that return no results."""
    response = await async_client.get("/api/audit/events?actor=nonexistent_user")
    assert response.status_code == 200
    data = response.json()

    assert data["events"] == []
    assert data["pagination"]["total_count"] == 0
    assert data["pagination"]["total_pages"] == 0
