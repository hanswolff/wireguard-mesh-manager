"""Test database migration with sample data for mesh topology.

This test validates that the mesh topology migration correctly handles
existing data from a pre-migration database.

Note: Migration history has been squashed into the initial schema. This test
still validates the expected post-migration state manually for legacy data.
"""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text

_NETWORKS_TABLE_SCHEMA_PRE = """
CREATE TABLE wireguard_networks (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    network_cidr VARCHAR(18) NOT NULL,
    listen_port INTEGER NOT NULL DEFAULT 51820,
    dns_servers VARCHAR(500),
    mtu INTEGER,
    persistent_keepalive INTEGER,
    private_key_encrypted TEXT NOT NULL,
    public_key VARCHAR(44) NOT NULL,
    preshared_key_encrypted TEXT,
    interface_properties JSON,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    CHECK (LENGTH(network_cidr) >= 9 AND LENGTH(network_cidr) <= 18 AND network_cidr LIKE '%.%/%'),
    CHECK (listen_port > 0 AND listen_port <= 65535),
    CHECK (mtu > 0 AND mtu <= 9000),
    CHECK (persistent_keepalive IS NULL OR (persistent_keepalive >= 0 AND persistent_keepalive <= 86400))
)
"""

_LOCATIONS_TABLE_SCHEMA = """
CREATE TABLE locations (
    id VARCHAR(36) PRIMARY KEY,
    network_id VARCHAR(36) NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    external_endpoint VARCHAR(255),
    internal_endpoint VARCHAR(255),
    preshared_key_encrypted TEXT,
    interface_properties JSON,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY (network_id) REFERENCES wireguard_networks(id) ON DELETE CASCADE,
    CHECK (external_endpoint IS NULL OR (LENGTH(external_endpoint) > 0 AND external_endpoint LIKE '%:%')),
    CHECK (internal_endpoint IS NULL OR (LENGTH(internal_endpoint) > 0 AND internal_endpoint LIKE '%:%')),
    CHECK (preshared_key_encrypted IS NULL OR LENGTH(preshared_key_encrypted) > 0)
)
"""

_DEVICES_TABLE_SCHEMA_PRE = """
CREATE TABLE devices (
    id VARCHAR(36) PRIMARY KEY,
    network_id VARCHAR(36) NOT NULL,
    location_id VARCHAR(36) NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    wireguard_ip VARCHAR(15),
    private_key_encrypted TEXT NOT NULL,
    public_key VARCHAR(44) NOT NULL,
    preshared_key_encrypted TEXT,
    enabled BOOLEAN NOT NULL DEFAULT 1,
    interface_properties JSON,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE CASCADE,
    FOREIGN KEY (network_id) REFERENCES wireguard_networks(id) ON DELETE CASCADE,
    CHECK (LENGTH(public_key) = 44),
    CHECK (preshared_key_encrypted IS NULL OR LENGTH(preshared_key_encrypted) > 0),
    CHECK (wireguard_ip IS NULL OR (LENGTH(wireguard_ip) >= 7 AND LENGTH(wireguard_ip) <= 15 AND wireguard_ip LIKE '%.%.%.%')),
    CHECK (wireguard_ip IS NULL OR (wireguard_ip NOT LIKE '0.%' AND wireguard_ip NOT LIKE '255.%'))
)
"""

_NETWORKS_TABLE_SCHEMA_POST = """
CREATE TABLE wireguard_networks_new (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    network_cidr VARCHAR(18) NOT NULL,
    dns_servers VARCHAR(500),
    mtu INTEGER,
    persistent_keepalive INTEGER,
    private_key_encrypted TEXT,
    public_key VARCHAR(44),
    preshared_key_encrypted TEXT,
    interface_properties JSON,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    CHECK (LENGTH(network_cidr) >= 9 AND LENGTH(network_cidr) <= 18 AND network_cidr LIKE '%.%/%'),
    CHECK (mtu IS NULL OR (mtu > 0 AND mtu <= 9000)),
    CHECK (persistent_keepalive IS NULL OR (persistent_keepalive >= 0 AND persistent_keepalive <= 86400))
)
"""

_DEVICES_TABLE_SCHEMA_POST = """
CREATE TABLE devices_new (
    id VARCHAR(36) PRIMARY KEY,
    network_id VARCHAR(36) NOT NULL,
    location_id VARCHAR(36) NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    wireguard_ip VARCHAR(15),
    private_key_encrypted TEXT NOT NULL,
    public_key VARCHAR(56) NOT NULL,
    preshared_key_encrypted TEXT,
    enabled BOOLEAN NOT NULL DEFAULT 1,
    external_endpoint_host VARCHAR(255),
    external_endpoint_port INTEGER,
    internal_endpoint_host VARCHAR(255),
    internal_endpoint_port INTEGER,
    location_preshared_key_encrypted TEXT,
    interface_properties JSON,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE CASCADE,
    FOREIGN KEY (network_id) REFERENCES wireguard_networks(id) ON DELETE CASCADE,
    CHECK (LENGTH(public_key) IN (44, 45, 56)),
    CHECK (preshared_key_encrypted IS NULL OR LENGTH(preshared_key_encrypted) > 0),
    CHECK (wireguard_ip IS NULL OR (LENGTH(wireguard_ip) >= 7 AND LENGTH(wireguard_ip) <= 15 AND wireguard_ip LIKE '%.%.%.%')),
    CHECK (wireguard_ip IS NULL OR (wireguard_ip NOT LIKE '0.%' AND wireguard_ip NOT LIKE '255.%')),
    CHECK (external_endpoint_host IS NULL OR LENGTH(external_endpoint_host) > 0),
    CHECK (external_endpoint_port IS NULL OR (external_endpoint_port >= 1 AND external_endpoint_port <= 65535)),
    CHECK (external_endpoint_host IS NULL OR external_endpoint_port IS NOT NULL),
    CHECK (internal_endpoint_host IS NULL OR LENGTH(internal_endpoint_host) > 0),
    CHECK (internal_endpoint_port IS NULL OR (internal_endpoint_port >= 1 AND internal_endpoint_port <= 65535)),
    CHECK ((internal_endpoint_host IS NULL AND internal_endpoint_port IS NULL) OR (internal_endpoint_host IS NOT NULL AND internal_endpoint_port IS NOT NULL)),
    CHECK (location_preshared_key_encrypted IS NULL OR LENGTH(location_preshared_key_encrypted) > 0)
)
"""


def generate_test_public_key() -> str:
    unique_id = uuid4().hex + uuid4().hex
    return (unique_id[:44] + "=" * 44)[:44]


def generate_test_private_key_encrypted() -> str:
    return f"encrypted_{uuid4().hex}"


class TestMigrationWithSampleData:
    @pytest.fixture
    def migration_db_path(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            yield tmp_file.name
        path = Path(tmp_file.name)
        if path.exists():
            path.unlink()

    def _create_pre_migration_database_with_data(
        self, db_path: str
    ) -> tuple[str, list[str], list[str]]:
        now = datetime.now(UTC).isoformat()
        engine = create_engine(f"sqlite:///{db_path}")

        self._create_pre_migration_schema(engine)
        network_id = self._insert_sample_network(engine, now)
        location_ids = self._insert_sample_locations(engine, network_id, now)
        device_ids = self._insert_sample_devices(engine, network_id, location_ids, now)

        engine.dispose()
        return network_id, location_ids, device_ids

    def _create_pre_migration_schema(self, engine) -> None:
        with engine.connect() as conn:
            conn.execute(text(_NETWORKS_TABLE_SCHEMA_PRE))
            conn.execute(text(_LOCATIONS_TABLE_SCHEMA))
            conn.execute(text(_DEVICES_TABLE_SCHEMA_PRE))
            conn.commit()

    def _insert_sample_network(self, engine, now: str) -> str:
        network_id = str(uuid4())
        with engine.connect() as conn:
            conn.execute(
                text(
                    """
                INSERT INTO wireguard_networks (
                    id, name, description, network_cidr, listen_port, dns_servers,
                    mtu, persistent_keepalive, private_key_encrypted, public_key,
                    preshared_key_encrypted, interface_properties, created_at, updated_at
                ) VALUES (
                    :id, :name, :description, :network_cidr, :listen_port, :dns_servers,
                    :mtu, :persistent_keepalive, :private_key_encrypted, :public_key,
                    :preshared_key_encrypted, :interface_properties, :created_at, :updated_at
                )
                """
                ),
                {
                    "id": network_id,
                    "name": "Sample Production Network",
                    "description": "A production network for testing migration",
                    "network_cidr": "10.10.0.0/24",
                    "listen_port": 51820,
                    "dns_servers": "1.1.1.1, 8.8.8.8",
                    "mtu": 1420,
                    "persistent_keepalive": 25,
                    "private_key_encrypted": generate_test_private_key_encrypted(),
                    "public_key": generate_test_public_key(),
                    "preshared_key_encrypted": "encrypted_preshared_key",
                    "interface_properties": '{"some": "config"}',
                    "created_at": now,
                    "updated_at": now,
                },
            )
            conn.commit()
        return network_id

    def _insert_sample_locations(self, engine, network_id: str, now: str) -> list[str]:
        locations_data = [
            (
                "Data Center A",
                "Primary data center",
                "dc-a.example.com:51820",
                "10.0.1.1:51820",
            ),
            (
                "Data Center B",
                "Secondary data center",
                "dc-b.example.com:51820",
                "10.0.2.1:51820",
            ),
            (
                "Branch Office",
                "Remote branch office",
                "branch.example.com:51820",
                "10.0.3.1:51820",
            ),
        ]

        location_ids = []
        with engine.connect() as conn:
            for name, description, external, internal in locations_data:
                location_id = str(uuid4())
                conn.execute(
                    text(
                        """
                    INSERT INTO locations (
                        id, network_id, name, description, external_endpoint, internal_endpoint,
                        created_at, updated_at
                    ) VALUES (
                        :id, :network_id, :name, :description, :external_endpoint, :internal_endpoint,
                        :created_at, :updated_at
                    )
                    """
                    ),
                    {
                        "id": location_id,
                        "network_id": network_id,
                        "name": name,
                        "description": description,
                        "external_endpoint": external,
                        "internal_endpoint": internal,
                        "created_at": now,
                        "updated_at": now,
                    },
                )
                location_ids.append(location_id)
            conn.commit()
        return location_ids

    def _insert_sample_devices(
        self, engine, network_id: str, location_ids: list[str], now: str
    ) -> list[str]:
        devices_data = [
            (
                location_ids[0],
                "DC-A-Server-1",
                "Server 1 in Data Center A",
                "10.10.0.1",
            ),
            (
                location_ids[0],
                "DC-A-Server-2",
                "Server 2 in Data Center A",
                "10.10.0.2",
            ),
            (
                location_ids[1],
                "DC-B-Server-1",
                "Server 1 in Data Center B",
                "10.10.0.3",
            ),
            (
                location_ids[1],
                "DC-B-Server-2",
                "Server 2 in Data Center B",
                "10.10.0.4",
            ),
            (
                location_ids[2],
                "Branch-Gateway",
                "Gateway for branch office",
                "10.10.0.5",
            ),
        ]

        device_ids = []
        with engine.connect() as conn:
            for location_id, name, description, wireguard_ip in devices_data:
                device_id = str(uuid4())
                conn.execute(
                    text(
                        """
                    INSERT INTO devices (
                        id, network_id, location_id, name, description, wireguard_ip,
                        private_key_encrypted, public_key, preshared_key_encrypted,
                        enabled, created_at, updated_at
                    ) VALUES (
                        :id, :network_id, :location_id, :name, :description, :wireguard_ip,
                        :private_key_encrypted, :public_key, :preshared_key_encrypted,
                        :enabled, :created_at, :updated_at
                    )
                    """
                    ),
                    {
                        "id": device_id,
                        "network_id": network_id,
                        "location_id": location_id,
                        "name": name,
                        "description": description,
                        "wireguard_ip": wireguard_ip,
                        "private_key_encrypted": generate_test_private_key_encrypted(),
                        "public_key": generate_test_public_key(),
                        "preshared_key_encrypted": None,
                        "enabled": True,
                        "created_at": now,
                        "updated_at": now,
                    },
                )
                device_ids.append(device_id)
            conn.commit()
        return device_ids

    def _apply_mesh_topology_migrations(self, db_path: str) -> None:
        engine = create_engine(f"sqlite:///{db_path}")

        with engine.connect() as conn:
            conn.execute(
                text(
                    "ALTER TABLE devices ADD COLUMN external_endpoint_host VARCHAR(255)"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE devices ADD COLUMN external_endpoint_port INTEGER"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE devices ADD COLUMN internal_endpoint_host VARCHAR(255)"
                )
            )
            conn.execute(
                text("ALTER TABLE devices ADD COLUMN internal_endpoint_port INTEGER")
            )

            conn.execute(text(_NETWORKS_TABLE_SCHEMA_POST))

            conn.execute(
                text(
                    """
                INSERT INTO wireguard_networks_new
                SELECT id, name, description, network_cidr, dns_servers, mtu, persistent_keepalive,
                       private_key_encrypted, public_key, preshared_key_encrypted,
                       interface_properties, created_at, updated_at
                FROM wireguard_networks
                """
                )
            )

            conn.execute(text("DROP TABLE wireguard_networks"))
            conn.execute(
                text("ALTER TABLE wireguard_networks_new RENAME TO wireguard_networks")
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_wireguard_networks_name ON wireguard_networks(name)"
                )
            )

            conn.execute(text(_DEVICES_TABLE_SCHEMA_POST))

            conn.execute(
                text(
                    """
                INSERT INTO devices_new
                SELECT id, network_id, location_id, name, description, wireguard_ip,
                       private_key_encrypted, public_key, preshared_key_encrypted,
                       enabled, external_endpoint_host, external_endpoint_port,
                       internal_endpoint_host, internal_endpoint_port,
                       NULL, interface_properties, created_at, updated_at
                FROM devices
                """
                )
            )

            conn.execute(text("DROP TABLE devices"))
            conn.execute(text("ALTER TABLE devices_new RENAME TO devices"))
            conn.execute(
                text(
                    "CREATE INDEX idx_devices_location_name ON devices(location_id, name)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_devices_network_ip ON devices(network_id, wireguard_ip)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_devices_network_public_key ON devices(network_id, public_key)"
                )
            )

            conn.commit()

        engine.dispose()

    def _verify_post_migration_state(
        self,
        migration_db_path: str,
        network_id: str,
        location_ids: list[str],
        device_ids: list[str],
    ) -> None:
        engine = create_engine(f"sqlite:///{migration_db_path}")
        with engine.connect() as conn:
            from sqlalchemy import inspect

            inspector = inspect(engine)

            self._verify_network_schema_changes(inspector)
            self._verify_device_schema_changes(inspector)
            self._verify_data_preservation(conn, network_id)

            try:
                conn.execute(text("SELECT listen_port FROM wireguard_networks"))
                raise AssertionError(
                    "listen_port column should not exist after migration"
                )
            except Exception:
                pass

        engine.dispose()

    def _verify_network_schema_changes(self, inspector) -> None:
        network_columns = inspector.get_columns("wireguard_networks")
        network_column_names = {col["name"] for col in network_columns}

        assert "listen_port" not in network_column_names

        nullable_key_fields = [
            "private_key_encrypted",
            "public_key",
            "preshared_key_encrypted",
        ]
        for col in network_columns:
            if col["name"] in nullable_key_fields:
                assert col["nullable"], f"{col['name']} should be nullable"

    def _verify_device_schema_changes(self, inspector) -> None:
        device_columns = inspector.get_columns("devices")
        device_column_names = {col["name"] for col in device_columns}

        assert "external_endpoint_host" in device_column_names
        assert "external_endpoint_port" in device_column_names
        assert "internal_endpoint_host" in device_column_names
        assert "internal_endpoint_port" in device_column_names

        for col in device_columns:
            if col["name"] == "public_key":
                assert col["type"].length >= 56

    def _verify_data_preservation(self, conn, network_id: str) -> None:
        result = conn.execute(text("SELECT COUNT(*) FROM wireguard_networks"))
        assert result.scalar_one() == 1

        result = conn.execute(text("SELECT COUNT(*) FROM locations"))
        assert result.scalar_one() == 3

        result = conn.execute(text("SELECT COUNT(*) FROM devices"))
        assert result.scalar_one() == 5

        result = conn.execute(
            text(
                """
                SELECT name, description, network_cidr, dns_servers, mtu,
                persistent_keepalive, private_key_encrypted, public_key,
                preshared_key_encrypted
                FROM wireguard_networks WHERE id = :network_id
                """
            ),
            {"network_id": network_id},
        )
        row = result.fetchone()
        assert row[0] == "Sample Production Network"
        assert row[1] == "A production network for testing migration"
        assert row[2] == "10.10.0.0/24"
        assert row[3] == "1.1.1.1, 8.8.8.8"
        assert row[4] == 1420
        assert row[5] == 25
        assert row[6] is not None
        assert row[7] is not None
        assert row[8] == "encrypted_preshared_key"

        result = conn.execute(text("SELECT COUNT(*) FROM devices WHERE enabled = 1"))
        assert result.scalar_one() == 5

    async def test_migration_preserves_sample_data(self, migration_db_path):
        network_id, location_ids, device_ids = (
            self._create_pre_migration_database_with_data(migration_db_path)
        )

        engine = create_engine(f"sqlite:///{migration_db_path}")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM wireguard_networks"))
            assert result.scalar_one() == 1

            result = conn.execute(text("SELECT COUNT(*) FROM locations"))
            assert result.scalar_one() == 3

            result = conn.execute(text("SELECT COUNT(*) FROM devices"))
            assert result.scalar_one() == 5

            result = conn.execute(
                text(
                    "SELECT listen_port FROM wireguard_networks WHERE id = :network_id"
                ),
                {"network_id": network_id},
            )
            assert result.scalar_one() == 51820

            result = conn.execute(text("PRAGMA table_info(devices)"))
            columns_before = [row[1] for row in result.fetchall()]
            assert "external_endpoint_host" not in columns_before
            assert "external_endpoint_port" not in columns_before
            assert "internal_endpoint_host" not in columns_before
            assert "internal_endpoint_port" not in columns_before

        engine.dispose()

        self._apply_mesh_topology_migrations(migration_db_path)

        self._verify_post_migration_state(
            migration_db_path, network_id, location_ids, device_ids
        )

    async def test_migration_with_empty_database(self, migration_db_path):
        network_id, location_ids, device_ids = (
            self._create_pre_migration_database_with_data(migration_db_path)
        )

        engine = create_engine(f"sqlite:///{migration_db_path}")
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM devices"))
            conn.execute(text("DELETE FROM locations"))
            conn.execute(text("DELETE FROM wireguard_networks"))
            conn.commit()
        engine.dispose()

        self._apply_mesh_topology_migrations(migration_db_path)

        engine = create_engine(f"sqlite:///{migration_db_path}")
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(wireguard_networks)"))
            network_columns = [row[1] for row in result.fetchall()]
            assert "listen_port" not in network_columns

            result = conn.execute(text("PRAGMA table_info(devices)"))
            device_columns = [row[1] for row in result.fetchall()]
            assert "external_endpoint_host" in device_columns
            assert "external_endpoint_port" in device_columns
            assert "internal_endpoint_host" in device_columns
            assert "internal_endpoint_port" in device_columns

            result = conn.execute(text("SELECT COUNT(*) FROM wireguard_networks"))
            assert result.scalar_one() == 0

            result = conn.execute(text("SELECT COUNT(*) FROM locations"))
            assert result.scalar_one() == 0

            result = conn.execute(text("SELECT COUNT(*) FROM devices"))
            assert result.scalar_one() == 0
        engine.dispose()
