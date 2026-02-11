"""Database models for WireGuard Mesh Manager."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    event,
)
from sqlalchemy.dialects import sqlite
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# JSON type for cross-database compatibility
JSON = sqlite.JSON().with_variant(sa.JSON(), "postgresql")

# Common column types
str_pk = Annotated[
    str, mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
]
uuid_pk = Annotated[UUID, mapped_column(Uuid, primary_key=True, default=uuid4)]
timestamp = Annotated[
    datetime,
    mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    ),
]
timestamp_nullable = Annotated[
    datetime, mapped_column(DateTime(timezone=True), nullable=True)
]


class Base(DeclarativeBase):
    """Base class for all database models."""

    created_at: Mapped[timestamp]
    updated_at: Mapped[timestamp]


@event.listens_for(Base, "before_update", propagate=True)
def receive_before_update(mapper: object, connection: object, target: Base) -> None:
    """Automatically update updated_at timestamp on model updates."""
    target.updated_at = datetime.now(UTC)


class WireGuardNetwork(Base):
    """Represents a WireGuard VPN network.

    For mesh topology, networks do not have their own WireGuard keys.
    Key fields are retained for backward compatibility with existing data.
    """

    __tablename__ = "wireguard_networks"

    id: Mapped[str_pk]
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    network_cidr: Mapped[str] = mapped_column(String(18), nullable=False)
    dns_servers: Mapped[str] = mapped_column(String(500), nullable=True)
    mtu: Mapped[int] = mapped_column(Integer, nullable=True)
    persistent_keepalive: Mapped[int] = mapped_column(Integer, nullable=True)
    # Key fields are optional for mesh topology compatibility
    private_key_encrypted: Mapped[str] = mapped_column(Text, nullable=True)
    public_key: Mapped[str] = mapped_column(String(44), nullable=True)
    preshared_key_encrypted: Mapped[str] = mapped_column(Text, nullable=True)
    interface_properties: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    locations: Mapped[list[Location]] = relationship(
        back_populates="network", cascade="all, delete-orphan"
    )
    devices: Mapped[list[Device]] = relationship(
        back_populates="network", cascade="all, delete-orphan"
    )
    api_keys: Mapped[list[APIKey]] = relationship(
        back_populates="network", cascade="all, delete-orphan"
    )
    audit_events: Mapped[list[AuditEvent]] = relationship(
        back_populates="network", cascade="all, delete-orphan"
    )
    device_peer_links: Mapped[list[DevicePeerLink]] = relationship(
        back_populates="network", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "LENGTH(network_cidr) >= 9 AND LENGTH(network_cidr) <= 18 AND network_cidr LIKE '%.%/%'",
            name="valid_network_cidr",
        ),
        CheckConstraint("mtu > 0 AND mtu <= 9000", name="valid_mtu_range"),
        CheckConstraint(
            "persistent_keepalive IS NULL OR (persistent_keepalive >= 0 AND persistent_keepalive <= 86400)",
            name="valid_keepalive_range",
        ),
        Index("idx_wireguard_networks_name", "name"),
    )


class Location(Base):
    """Represents a physical or logical location within a network."""

    __tablename__ = "locations"

    id: Mapped[str_pk]
    network_id: Mapped[str] = mapped_column(
        ForeignKey("wireguard_networks.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    external_endpoint: Mapped[str] = mapped_column(String(255), nullable=True)
    internal_endpoint: Mapped[str] = mapped_column(String(255), nullable=True)
    preshared_key_encrypted: Mapped[str] = mapped_column(Text, nullable=True)
    interface_properties: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    network: Mapped[WireGuardNetwork] = relationship(back_populates="locations")
    devices: Mapped[list[Device]] = relationship(
        back_populates="location", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "internal_endpoint IS NULL OR (LENGTH(internal_endpoint) > 0 AND internal_endpoint LIKE '%:%')",
            name="valid_internal_endpoint_format",
        ),
        CheckConstraint(
            "preshared_key_encrypted IS NULL OR LENGTH(preshared_key_encrypted) > 0",
            name="valid_location_preshared_key_length",
        ),
        Index("idx_locations_network_name", "network_id", "name", unique=True),
    )


class Device(Base):
    """Represents a WireGuard device/peer."""

    __tablename__ = "devices"

    id: Mapped[str_pk]
    network_id: Mapped[str] = mapped_column(
        ForeignKey("wireguard_networks.id", ondelete="CASCADE"), nullable=False
    )
    location_id: Mapped[str] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    wireguard_ip: Mapped[str | None] = mapped_column(String(15), nullable=True)
    external_endpoint_host: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    external_endpoint_port: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    internal_endpoint_host: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    internal_endpoint_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    private_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    device_dek_encrypted_master: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    device_dek_encrypted_api_key: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    public_key: Mapped[str] = mapped_column(String(56), nullable=False)
    preshared_key_encrypted: Mapped[str] = mapped_column(Text, nullable=True)
    network_preshared_key_encrypted: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    location_preshared_key_encrypted: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    interface_properties: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    network: Mapped[WireGuardNetwork] = relationship(back_populates="devices")
    location: Mapped[Location] = relationship(back_populates="devices")
    api_keys: Mapped[list[APIKey]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )
    outgoing_links: Mapped[list[DevicePeerLink]] = relationship(
        back_populates="from_device",
        cascade="all, delete-orphan",
        foreign_keys="DevicePeerLink.from_device_id",
    )
    incoming_links: Mapped[list[DevicePeerLink]] = relationship(
        back_populates="to_device",
        cascade="all, delete-orphan",
        foreign_keys="DevicePeerLink.to_device_id",
    )

    __table_args__ = (
        CheckConstraint(
            "wireguard_ip IS NULL OR (LENGTH(wireguard_ip) >= 7 AND LENGTH(wireguard_ip) <= 15 AND wireguard_ip LIKE '%.%.%.%')",
            name="valid_ipv4_address_format",
        ),
        # Basic format validation - detailed validation happens in service layer
        CheckConstraint(
            "wireguard_ip IS NULL OR (wireguard_ip NOT LIKE '0.%' AND wireguard_ip NOT LIKE '255.%')",
            name="valid_ip_bounds",
        ),
        CheckConstraint(
            "LENGTH(public_key) IN (44, 45, 56)",
            name="valid_public_key_length",
        ),
        CheckConstraint(
            "preshared_key_encrypted IS NULL OR LENGTH(preshared_key_encrypted) > 0",
            name="valid_preshared_key_length",
        ),
        CheckConstraint(
            "network_preshared_key_encrypted IS NULL OR LENGTH(network_preshared_key_encrypted) > 0",
            name="valid_network_preshared_key_length",
        ),
        CheckConstraint(
            "location_preshared_key_encrypted IS NULL OR LENGTH(location_preshared_key_encrypted) > 0",
            name="valid_location_preshared_key_encrypted_length",
        ),
        CheckConstraint(
            "external_endpoint_host IS NULL OR LENGTH(external_endpoint_host) > 0",
            name="valid_device_external_endpoint_host",
        ),
        CheckConstraint(
            "external_endpoint_port IS NULL OR (external_endpoint_port >= 1 AND external_endpoint_port <= 65535)",
            name="valid_device_external_endpoint_port",
        ),
        CheckConstraint(
            "external_endpoint_host IS NULL OR external_endpoint_port IS NOT NULL",
            name="valid_device_external_endpoint_pair",
        ),
        CheckConstraint(
            "internal_endpoint_host IS NULL OR LENGTH(internal_endpoint_host) > 0",
            name="valid_device_internal_endpoint_host",
        ),
        CheckConstraint(
            "internal_endpoint_port IS NULL OR (internal_endpoint_port >= 1 AND internal_endpoint_port <= 65535)",
            name="valid_device_internal_endpoint_port",
        ),
        CheckConstraint(
            "(internal_endpoint_host IS NULL AND internal_endpoint_port IS NULL) OR (internal_endpoint_host IS NOT NULL AND internal_endpoint_port IS NOT NULL)",
            name="valid_device_internal_endpoint_pair",
        ),
        Index("idx_devices_network_ip", "network_id", "wireguard_ip", unique=True),
        Index(
            "idx_devices_network_public_key", "network_id", "public_key", unique=True
        ),
        Index("idx_devices_location_name", "location_id", "name"),
    )


class DevicePeerLink(Base):
    """Represents directional per-device peer properties."""

    __tablename__ = "device_peer_links"

    id: Mapped[str_pk]
    network_id: Mapped[str] = mapped_column(
        ForeignKey("wireguard_networks.id", ondelete="CASCADE"), nullable=False
    )
    from_device_id: Mapped[str] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), nullable=False
    )
    to_device_id: Mapped[str] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), nullable=False
    )
    properties: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    preshared_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    preshared_key_encrypted_dek: Mapped[str | None] = mapped_column(Text, nullable=True)

    network: Mapped[WireGuardNetwork] = relationship(back_populates="device_peer_links")
    from_device: Mapped[Device] = relationship(
        back_populates="outgoing_links", foreign_keys=[from_device_id]
    )
    to_device: Mapped[Device] = relationship(
        back_populates="incoming_links", foreign_keys=[to_device_id]
    )

    __table_args__ = (
        CheckConstraint(
            "from_device_id != to_device_id", name="valid_device_peer_link_direction"
        ),
        CheckConstraint(
            "preshared_key_encrypted IS NULL OR LENGTH(preshared_key_encrypted) > 0",
            name="valid_device_peer_link_preshared_key_length",
        ),
        CheckConstraint(
            "preshared_key_encrypted_dek IS NULL OR LENGTH(preshared_key_encrypted_dek) > 0",
            name="valid_device_peer_link_preshared_key_dek_length",
        ),
        Index(
            "idx_device_peer_links_network_from_to",
            "network_id",
            "from_device_id",
            "to_device_id",
            unique=True,
        ),
        Index("idx_device_peer_links_from_device", "from_device_id"),
    )


class APIKey(Base):
    """Represents an API key for device config retrieval."""

    __tablename__ = "api_keys"

    id: Mapped[str_pk]
    network_id: Mapped[str] = mapped_column(
        ForeignKey("wireguard_networks.id", ondelete="CASCADE"), nullable=False
    )
    device_id: Mapped[str] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), nullable=False
    )
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    key_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    device_dek_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    allowed_ip_ranges: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_used_at: Mapped[timestamp_nullable]
    expires_at: Mapped[timestamp_nullable]

    # Relationships
    network: Mapped[WireGuardNetwork] = relationship(back_populates="api_keys")
    device: Mapped[Device] = relationship(back_populates="api_keys")

    __table_args__ = (
        CheckConstraint(
            "last_used_at IS NULL OR last_used_at >= created_at", name="valid_last_used"
        ),
        CheckConstraint(
            "expires_at IS NULL OR expires_at > created_at", name="valid_expiry"
        ),
        Index("idx_api_keys_network_hash", "network_id", "key_hash"),
        Index("idx_api_keys_device_fingerprint", "device_id", "key_fingerprint"),
        Index("idx_api_keys_device_enabled", "device_id", "enabled"),
    )


class AuditEvent(Base):
    """Append-only audit log for security events."""

    __tablename__ = "audit_events"

    id: Mapped[str_pk]
    network_id: Mapped[str] = mapped_column(
        ForeignKey("wireguard_networks.id", ondelete="CASCADE"), nullable=True
    )
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=True)
    details: Mapped[str] = mapped_column(Text, nullable=True)

    # Relationships
    network: Mapped[WireGuardNetwork] = relationship(back_populates="audit_events")
    __table_args__ = (
        CheckConstraint("LENGTH(actor) > 0", name="valid_actor_format"),
        Index("idx_audit_network_timestamp", "network_id", "created_at"),
        Index("idx_audit_actor_timestamp", "actor", "created_at"),
    )


class OperationalSetting(Base):
    """Represents a dynamic operational setting."""

    __tablename__ = "operational_settings"

    id: Mapped[str_pk]
    key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint("LENGTH(key) > 0", name="valid_setting_key"),
        CheckConstraint("LENGTH(value) > 0", name="valid_setting_value"),
        Index("idx_operational_settings_key", "key"),
    )
