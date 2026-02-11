"""initial_schema

Revision ID: ec9f54ea0982
Revises:
Create Date: 2025-12-19 18:12:53.824368

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ec9f54ea0982"  # pragma: allowlist secret
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create wireguard_networks table
    op.create_table(
        "wireguard_networks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("network_cidr", sa.String(length=18), nullable=False),
        sa.Column("dns_servers", sa.String(length=500), nullable=True),
        sa.Column("mtu", sa.Integer(), nullable=True),
        sa.Column("persistent_keepalive", sa.Integer(), nullable=True),
        sa.Column("private_key_encrypted", sa.Text(), nullable=True),
        sa.Column("public_key", sa.String(length=44), nullable=True),
        sa.Column("preshared_key_encrypted", sa.Text(), nullable=True),
        sa.Column("interface_properties", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "LENGTH(network_cidr) >= 9 AND LENGTH(network_cidr) <= 18 AND network_cidr LIKE '%.%/%'",
            name="valid_network_cidr",
        ),
        sa.CheckConstraint("mtu > 0 AND mtu <= 9000", name="valid_mtu_range"),
        sa.CheckConstraint(
            "persistent_keepalive IS NULL OR (persistent_keepalive >= 0 AND persistent_keepalive <= 86400)",
            name="valid_keepalive_range",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_wireguard_networks_name", "wireguard_networks", ["name"], unique=False
    )

    # Create locations table
    op.create_table(
        "locations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("network_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("external_endpoint", sa.String(length=255), nullable=True),
        sa.Column("internal_endpoint", sa.String(length=255), nullable=True),
        sa.Column("preshared_key_encrypted", sa.Text(), nullable=True),
        sa.Column("interface_properties", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "internal_endpoint IS NULL OR (LENGTH(internal_endpoint) > 0 AND internal_endpoint LIKE '%:%')",
            name="valid_internal_endpoint_format",
        ),
        sa.CheckConstraint(
            "preshared_key_encrypted IS NULL OR LENGTH(preshared_key_encrypted) > 0",
            name="valid_location_preshared_key_length",
        ),
        sa.ForeignKeyConstraint(
            ["network_id"], ["wireguard_networks.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_locations_network_name", "locations", ["network_id", "name"], unique=True
    )

    # Create devices table
    op.create_table(
        "devices",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("network_id", sa.String(length=36), nullable=False),
        sa.Column("location_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("wireguard_ip", sa.String(length=15), nullable=True),
        sa.Column("external_endpoint_host", sa.String(length=255), nullable=True),
        sa.Column("external_endpoint_port", sa.Integer(), nullable=True),
        sa.Column("internal_endpoint_host", sa.String(length=255), nullable=True),
        sa.Column("internal_endpoint_port", sa.Integer(), nullable=True),
        sa.Column("private_key_encrypted", sa.Text(), nullable=False),
        sa.Column("device_dek_encrypted_master", sa.Text(), nullable=True),
        sa.Column("device_dek_encrypted_api_key", sa.Text(), nullable=True),
        sa.Column("public_key", sa.String(length=56), nullable=False),
        sa.Column("preshared_key_encrypted", sa.Text(), nullable=True),
        sa.Column("network_preshared_key_encrypted", sa.Text(), nullable=True),
        sa.Column("location_preshared_key_encrypted", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("interface_properties", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "LENGTH(public_key) IN (44, 45, 56)", name="valid_public_key_length"
        ),
        sa.CheckConstraint(
            "preshared_key_encrypted IS NULL OR LENGTH(preshared_key_encrypted) > 0",
            name="valid_preshared_key_length",
        ),
        sa.CheckConstraint(
            "network_preshared_key_encrypted IS NULL OR LENGTH(network_preshared_key_encrypted) > 0",
            name="valid_network_preshared_key_length",
        ),
        sa.CheckConstraint(
            "location_preshared_key_encrypted IS NULL OR LENGTH(location_preshared_key_encrypted) > 0",
            name="valid_location_preshared_key_encrypted_length",
        ),
        sa.CheckConstraint(
            "wireguard_ip IS NULL OR (LENGTH(wireguard_ip) >= 7 AND LENGTH(wireguard_ip) <= 15 AND wireguard_ip LIKE '%.%.%.%')",
            name="valid_ipv4_address_format",
        ),
        sa.CheckConstraint(
            "wireguard_ip IS NULL OR (wireguard_ip NOT LIKE '0.%' AND wireguard_ip NOT LIKE '255.%')",
            name="valid_ip_bounds",
        ),
        sa.CheckConstraint(
            "external_endpoint_host IS NULL OR LENGTH(external_endpoint_host) > 0",
            name="valid_device_external_endpoint_host",
        ),
        sa.CheckConstraint(
            "external_endpoint_port IS NULL OR (external_endpoint_port >= 1 AND external_endpoint_port <= 65535)",
            name="valid_device_external_endpoint_port",
        ),
        sa.CheckConstraint(
            "external_endpoint_host IS NULL OR external_endpoint_port IS NOT NULL",
            name="valid_device_external_endpoint_pair",
        ),
        sa.CheckConstraint(
            "internal_endpoint_host IS NULL OR LENGTH(internal_endpoint_host) > 0",
            name="valid_device_internal_endpoint_host",
        ),
        sa.CheckConstraint(
            "internal_endpoint_port IS NULL OR (internal_endpoint_port >= 1 AND internal_endpoint_port <= 65535)",
            name="valid_device_internal_endpoint_port",
        ),
        sa.CheckConstraint(
            "(internal_endpoint_host IS NULL AND internal_endpoint_port IS NULL) OR (internal_endpoint_host IS NOT NULL AND internal_endpoint_port IS NOT NULL)",
            name="valid_device_internal_endpoint_pair",
        ),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["network_id"], ["wireguard_networks.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_devices_location_name", "devices", ["location_id", "name"], unique=False
    )
    op.create_index(
        "idx_devices_network_ip", "devices", ["network_id", "wireguard_ip"], unique=True
    )
    op.create_index(
        "idx_devices_network_public_key",
        "devices",
        ["network_id", "public_key"],
        unique=True,
    )

    # Create device_peer_links table
    op.create_table(
        "device_peer_links",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("network_id", sa.String(length=36), nullable=False),
        sa.Column("from_device_id", sa.String(length=36), nullable=False),
        sa.Column("to_device_id", sa.String(length=36), nullable=False),
        sa.Column("properties", sa.JSON(), nullable=True),
        sa.Column("preshared_key_encrypted", sa.Text(), nullable=True),
        sa.Column("preshared_key_encrypted_dek", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "from_device_id != to_device_id",
            name="valid_device_peer_link_direction",
        ),
        sa.CheckConstraint(
            "preshared_key_encrypted IS NULL OR LENGTH(preshared_key_encrypted) > 0",
            name="valid_device_peer_link_preshared_key_length",
        ),
        sa.CheckConstraint(
            "preshared_key_encrypted_dek IS NULL OR LENGTH(preshared_key_encrypted_dek) > 0",
            name="valid_device_peer_link_preshared_key_dek_length",
        ),
        sa.ForeignKeyConstraint(
            ["from_device_id"], ["devices.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["to_device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["network_id"], ["wireguard_networks.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_device_peer_links_from_device",
        "device_peer_links",
        ["from_device_id"],
        unique=False,
    )
    op.create_index(
        "idx_device_peer_links_network_from_to",
        "device_peer_links",
        ["network_id", "from_device_id", "to_device_id"],
        unique=True,
    )

    # Create audit_events table
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("network_id", sa.String(length=36), nullable=True),
        sa.Column("actor", sa.String(length=255), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=50), nullable=False),
        sa.Column("resource_id", sa.String(length=36), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("LENGTH(actor) > 0", name="valid_actor_format"),
        sa.ForeignKeyConstraint(
            ["network_id"], ["wireguard_networks.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_audit_actor_timestamp",
        "audit_events",
        ["actor", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_audit_network_timestamp",
        "audit_events",
        ["network_id", "created_at"],
        unique=False,
    )

    # Create api_keys table
    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("network_id", sa.String(length=36), nullable=False),
        sa.Column("device_id", sa.String(length=36), nullable=False),
        sa.Column("key_hash", sa.String(length=255), nullable=False),
        sa.Column("key_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("device_dek_encrypted", sa.Text(), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("allowed_ip_ranges", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "expires_at IS NULL OR expires_at > created_at", name="valid_expiry"
        ),
        sa.CheckConstraint(
            "last_used_at IS NULL OR last_used_at >= created_at", name="valid_last_used"
        ),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["network_id"], ["wireguard_networks.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_api_keys_device_enabled", "api_keys", ["device_id", "enabled"])
    op.create_index(
        "idx_api_keys_device_fingerprint",
        "api_keys",
        ["device_id", "key_fingerprint"],
    )
    op.create_index("idx_api_keys_network_hash", "api_keys", ["network_id", "key_hash"])

    # Create operational_settings table
    op.create_table(
        "operational_settings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False, unique=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("LENGTH(key) > 0", name="valid_setting_key"),
        sa.CheckConstraint("LENGTH(value) > 0", name="valid_setting_value"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_operational_settings_key", "operational_settings", ["key"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("device_peer_links")
    op.drop_table("operational_settings")
    op.drop_table("api_keys")
    op.drop_table("audit_events")
    op.drop_table("devices")
    op.drop_table("locations")
    op.drop_table("wireguard_networks")
