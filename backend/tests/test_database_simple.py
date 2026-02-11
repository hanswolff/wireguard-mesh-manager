"""Simple database schema test."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.database.models import WireGuardNetwork


@pytest.mark.asyncio
async def test_database_connection(db_session) -> None:
    """Test database connection and basic table existence."""
    result = await db_session.execute(select(WireGuardNetwork))
    networks = result.scalars().all()
    assert isinstance(networks, list)
    assert len(networks) == 0


@pytest.mark.asyncio
async def test_create_network(db_session, sample_network_data) -> None:
    """Test creating a simple network record."""
    network = WireGuardNetwork(**sample_network_data)
    db_session.add(network)
    await db_session.commit()
    await db_session.refresh(network)

    # Verify the network was created
    result = await db_session.execute(
        select(WireGuardNetwork).where(
            WireGuardNetwork.name == sample_network_data["name"]
        )
    )
    db_network = result.scalar_one()
    assert db_network.name == sample_network_data["name"]
    assert db_network.network_cidr == sample_network_data["network_cidr"]
    assert db_network.description == sample_network_data["description"]
