"""Debug test to check validation errors."""

import pytest
from httpx import AsyncClient

from app.utils.logging import get_logger

logger = get_logger(__name__)

pytestmark = pytest.mark.usefixtures("unlocked_master_password")


async def test_debug_create_network(async_client: AsyncClient) -> None:
    """Debug network creation."""
    network_data = {
        "name": "Test Network",
        "description": "A test network",
        "network_cidr": "10.0.0.0/24",
    }
    response = await async_client.post("/api/networks/", json=network_data)

    logger.info(
        "Debug network creation response",
        extra={
            "status_code": response.status_code,
            "response_body": response.text,
            "headers": dict(response.headers) if response.status_code != 201 else None,
        },
    )

    assert response.status_code == 201
