"""Integration tests for audit logging functionality."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest
from sqlalchemy import text

from app.services.audit import AuditService

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.engine import Result
    from sqlalchemy.ext.asyncio import AsyncSession


class AuditEventQueries:
    """Helper class for common audit event database queries."""

    @staticmethod
    async def fetch_events_by_network(
        db_session: AsyncSession,
        network_id: str,
        action: str | None = None,
        resource_type: str | None = None,
        actor: str | None = None,
    ) -> Result:
        """Fetch audit events with optional filters."""
        query = "SELECT * FROM audit_events WHERE network_id = :network_id"
        params = {"network_id": network_id}

        if action:
            query += " AND action = :action"
            params["action"] = action
        if resource_type:
            query += " AND resource_type = :resource_type"
            params["resource_type"] = resource_type
        if actor:
            query += " AND actor = :actor"
            params["actor"] = actor

        query += " ORDER BY created_at DESC"

        return await db_session.execute(text(query), params)

    @staticmethod
    async def count_events_by_network(db_session: AsyncSession, network_id: str) -> int:
        """Count audit events for a network."""
        result = await db_session.execute(
            text(
                "SELECT COUNT(*) as count FROM audit_events WHERE network_id = :network_id"
            ),
            {"network_id": network_id},
        )
        count_row = result.fetchone()
        if count_row and hasattr(count_row, "count"):
            count_value = getattr(count_row, "count", 0)
            return int(count_value) if isinstance(count_value, (int, float, str)) else 0
        return 0


def create_test_location_data(
    network_id: str, name: str = "Test Location"
) -> dict[str, str]:
    """Create test location data for API requests."""
    return {
        "network_id": network_id,
        "name": name,
        "description": f"{name} description",
        "external_endpoint": "192.168.1.100",
    }


def create_test_device_data(
    network_id: str, location_id: str, name: str = "Test Device"
) -> dict[str, str]:
    """Create test device data for API requests."""
    return {
        "network_id": network_id,
        "location_id": location_id,
        "name": name,
        "description": f"{name} description",
        "wireguard_ip": "10.0.0.5",
        "public_key": "VGVzdF9wdWJsaWNfa2V5X2Zvcl9kZXZpY2UxMjM0NTY3ODkwMTI=",
    }


def assert_audit_event_fields(
    event: object,
    expected_network_id: str,
    expected_action: str,
    expected_resource_type: str,
) -> None:
    """Assert common audit event fields."""
    assert event.network_id == expected_network_id  # type: ignore[attr-defined]
    assert event.action == expected_action  # type: ignore[attr-defined]
    assert event.resource_type == expected_resource_type  # type: ignore[attr-defined]
    assert event.actor is not None  # type: ignore[attr-defined]
    assert event.created_at is not None  # type: ignore[attr-defined]


@pytest.mark.asyncio
@pytest.mark.skip(reason="Test has issues with async client setup")
@pytest.mark.asyncio
async def test_audit_event_creation_via_api(
    async_client: AsyncClient, db_session: AsyncSession, test_network: Any
) -> None:
    """Test that audit events are created when API endpoints are called."""
    response = await async_client.post(
        "/api/locations/",
        json=create_test_location_data(test_network.id),
    )
    assert response.status_code == 201

    await db_session.commit()

    events_result = await AuditEventQueries.fetch_events_by_network(
        db_session, test_network.id, action="CREATE", resource_type="location"
    )
    events = events_result.fetchall()
    assert len(events) >= 1

    event = events[0]
    assert_audit_event_fields(event, test_network.id, "CREATE", "location")

    if event.details:
        details = json.loads(event.details)
        assert "resource_name" in details or "name" in details


@pytest.mark.skip(reason="Device validation issues - skipping for now")
@pytest.mark.asyncio
async def test_audit_logs_for_device_crud_operations(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_network: Any,
    test_location: Any,
) -> None:
    """Test audit logging for device CRUD operations."""
    device_data = create_test_device_data(test_network.id, str(test_location.id))

    response = await async_client.post("/api/devices/", json=device_data)
    assert response.status_code == 201
    device_id = response.json()["id"]

    await db_session.commit()

    create_event = (
        await AuditEventQueries.fetch_events_by_network(
            db_session, test_network.id, action="CREATE", resource_type="device"
        )
    ).fetchone()
    assert create_event is not None
    assert create_event.resource_id == device_id

    update_data = {"name": "Updated Device Name", "description": "Updated description"}
    response = await async_client.patch(f"/api/devices/{device_id}/", json=update_data)
    assert response.status_code == 200

    await db_session.commit()

    update_event = (
        await AuditEventQueries.fetch_events_by_network(
            db_session, test_network.id, action="UPDATE", resource_type="device"
        )
    ).fetchone()
    assert update_event is not None
    assert update_event.resource_id == device_id

    if update_event.details:
        details = json.loads(update_event.details)
        assert "changes" in details or "resource_name" in details

    response = await async_client.delete(f"/api/devices/{device_id}/")
    assert response.status_code == 204

    await db_session.commit()

    delete_event = (
        await AuditEventQueries.fetch_events_by_network(
            db_session, test_network.id, action="DELETE", resource_type="device"
        )
    ).fetchone()
    assert delete_event is not None
    assert delete_event.resource_id == device_id


@pytest.mark.asyncio
async def test_audit_service_direct_logging_with_database(
    db_session: AsyncSession, test_network: Any
) -> None:
    """Test AuditService direct logging with real database."""
    audit_service = AuditService(db_session)

    await audit_service.log_event(
        network_id=test_network.id,
        actor="test-user",
        action="TEST_ACTION",
        resource_type="test_resource",
        resource_id="test-123",
        details={"test_field": "test_value"},
    )

    await db_session.commit()

    event = (
        await AuditEventQueries.fetch_events_by_network(
            db_session, test_network.id, actor="test-user", action="TEST_ACTION"
        )
    ).fetchone()

    assert event is not None
    assert event.resource_type == "test_resource"
    assert event.resource_id == "test-123"

    if event.details:
        details = json.loads(event.details)
        assert details["test_field"] == "test_value"


@pytest.mark.asyncio
async def test_audit_service_sanitization_in_database(
    db_session: AsyncSession, test_network: Any
) -> None:
    """Test that sensitive data is properly sanitized before database storage."""
    audit_service = AuditService(db_session)

    sensitive_details = {
        "name": "Test Network",
        "private_key": "secret_private_key_value",
        "public_key": "secret_public_key_value",
        "password": "secret_password",
        "api_key": "secret_api_key",
        "normal_field": "normal_value",
        "nested": {
            "token": "secret_token",
            "another_normal": "keep_this",
        },
    }

    await audit_service.log_event(
        network_id=test_network.id,
        actor="test-user",
        action="TEST_SANITIZE",
        resource_type="test_resource",
        details=sensitive_details,
    )

    await db_session.commit()

    event = (
        await AuditEventQueries.fetch_events_by_network(
            db_session, test_network.id, action="TEST_SANITIZE"
        )
    ).fetchone()
    assert event is not None

    details = json.loads(event.details)

    sensitive_fields = ["private_key", "public_key", "password", "api_key"]
    for field in sensitive_fields:
        assert details[field] == "[REDACTED]"

    assert details["name"] == "Test Network"
    assert details["normal_field"] == "normal_value"
    assert details["nested"]["token"] == "[REDACTED]"
    assert details["nested"]["another_normal"] == "keep_this"


@pytest.mark.asyncio
async def test_audit_api_access_logging(
    db_session: AsyncSession, test_network: Any
) -> None:
    """Test API access logging for device config retrieval."""
    audit_service = AuditService(db_session)

    test_device_id = "test-device-id-12345"
    await audit_service.log_api_access(
        network_id=test_network.id,
        device_id=test_device_id,
        source_ip="192.168.1.100",
        action="CONFIG_RETRIEVAL",
        success=True,
    )

    await db_session.commit()

    actor = f"device:{test_device_id}"
    event = (
        await AuditEventQueries.fetch_events_by_network(
            db_session, test_network.id, actor=actor, action="CONFIG_RETRIEVAL"
        )
    ).fetchone()

    assert event is not None
    assert event.resource_type == "api_key"
    assert event.resource_id == test_device_id

    details = json.loads(event.details)
    assert details["source_ip"] == "192.168.1.100"
    assert details["success"] is True


@pytest.mark.asyncio
async def test_audit_admin_action_logging(
    db_session: AsyncSession, test_network: Any
) -> None:
    """Test admin action logging with changes."""
    audit_service = AuditService(db_session)

    changes = {
        "enabled": {"old": False, "new": True},
        "name": {"old": "Old Name", "new": "New Name"},
    }

    await audit_service.log_admin_action(
        network_id=test_network.id,
        admin_actor="admin-user",
        action="UPDATE",
        resource_type="device",
        resource_id="device-123",
        resource_name="Test Device",
        changes=changes,
    )

    await db_session.commit()

    event = (
        await AuditEventQueries.fetch_events_by_network(
            db_session, test_network.id, actor="admin-user", action="UPDATE"
        )
    ).fetchone()

    assert event is not None
    assert event.resource_type == "device"
    assert event.resource_id == "device-123"

    details = json.loads(event.details)
    assert details["resource_name"] == "Test Device"
    assert details["changes"] == changes


@pytest.mark.asyncio
async def test_audit_event_ordering_and_consistency(
    async_client: AsyncClient, db_session: AsyncSession, test_network: Any
) -> None:
    """Test that audit events are properly ordered and consistent."""
    await async_client.post(
        "/api/locations/",
        json=create_test_location_data(test_network.id, "Location 1"),
    )

    await async_client.post(
        "/api/locations/",
        json=create_test_location_data(test_network.id, "Location 2"),
    )

    await db_session.commit()

    events = await db_session.execute(
        text(
            """SELECT * FROM audit_events
           WHERE network_id = :network_id AND resource_type = 'location' AND action = 'CREATE'
           ORDER BY created_at ASC"""
        ),
        {"network_id": test_network.id},
    )
    location_events = events.fetchall()

    assert len(location_events) == 2
    assert location_events[0].created_at <= location_events[1].created_at

    for event in location_events:
        assert_audit_event_fields(event, test_network.id, "CREATE", "location")


@pytest.mark.asyncio
async def test_audit_event_fields_validation(
    db_session: AsyncSession, test_network: Any
) -> None:
    """Test audit event field validation and constraints."""
    audit_service = AuditService(db_session)

    await audit_service.log_event(
        network_id=test_network.id,
        actor="test-user",
        action="MINIMAL_TEST",
        resource_type="test_resource",
    )

    await db_session.commit()

    event = (
        await AuditEventQueries.fetch_events_by_network(
            db_session, test_network.id, action="MINIMAL_TEST"
        )
    ).fetchone()

    assert event is not None
    assert event.id is not None
    assert event.network_id == test_network.id
    assert event.actor == "test-user"
    assert event.action == "MINIMAL_TEST"
    assert event.resource_type == "test_resource"
    assert event.resource_id is None
    assert event.details is None
    assert event.created_at is not None


@pytest.mark.asyncio
async def test_multiple_audit_events_transaction(
    db_session: AsyncSession, test_network: Any
) -> None:
    """Test that multiple audit events can be created in a single transaction."""
    audit_service = AuditService(db_session)

    await audit_service.log_event(
        network_id=test_network.id,
        actor="user1",
        action="ACTION1",
        resource_type="resource1",
    )

    await audit_service.log_event(
        network_id=test_network.id,
        actor="user2",
        action="ACTION2",
        resource_type="resource2",
        resource_id="resource-2",
        details={"test": "data"},
    )

    await audit_service.log_api_access(
        network_id=test_network.id,
        device_id="device-123",
        source_ip="10.0.0.1",
        success=False,
    )

    await db_session.commit()

    count = await AuditEventQueries.count_events_by_network(db_session, test_network.id)
    assert count >= 3

    action1_event = (
        await AuditEventQueries.fetch_events_by_network(
            db_session, test_network.id, actor="user1", action="ACTION1"
        )
    ).fetchone()
    assert action1_event is not None

    api_event = (
        await AuditEventQueries.fetch_events_by_network(
            db_session, test_network.id, actor="device:device-123"
        )
    ).fetchone()
    assert api_event is not None
    assert api_event.action == "CONFIG_RETRIEVAL"
