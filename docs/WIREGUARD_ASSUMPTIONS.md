# WireGuard assumptions and deployment examples

This guide documents the expectations baked into configuration generation and API flows. Use it as a pre-flight checklist before deploying.

For comprehensive documentation on mesh topology architecture, including endpoint selection rules, deployment patterns, and implementation details, see [Mesh Topology Architecture](MESH_TOPOLOGY_ARCHITECTURE.md).

## Supported topologies

WireGuard Mesh Manager uses a **mesh topology** by default, where all devices connect directly to each other without a central WireGuard server.

### Mesh Topology

In mesh topology:

- **No central server**: Unlike traditional hub-and-spoke setups, there is no single WireGuard server that all devices connect to. Every device can connect to every other device in the network.
- **Full peer mesh**: Each device's configuration includes all other enabled devices in the network as peers.
- **Direct device-to-device connectivity**: Devices establish direct WireGuard tunnels with each other, enabling optimal routing paths and reducing single points of failure.

### Deployment Patterns

- **Site-to-site mesh**: Multiple locations (data centers, branches, cloud regions) connected together. Each device has both internal and external endpoints; peers in the same location use the internal endpoint, while cross-location peers use the external endpoint.
- **Road-warrior/remote access**: Roaming clients connect to a specific location (typically the one with internet egress). External endpoints are required for roaming clients so they can reach a gateway from the public internet.

## Endpoint selection rules

The system automatically selects the appropriate endpoint based on location relationships:

- **Same location**: peers use the **internal** endpoint to stay on private networks and avoid hairpinning. This keeps traffic within the local network segment and reduces latency.
- **Different locations**: peers use the **external** endpoint so sites and roaming clients can reach each other over the internet. This enables connectivity across network boundaries.
- **Fallback behavior**: If a device has no internal endpoint configured, the location-level internal endpoint is used. If neither is available, the external endpoint is used even for same-location peers.

### Endpoint Requirements

- **External endpoints**: Must be publicly reachable (public IP or DNS with port) with proper NAT/firewall rules allowing UDP traffic (typically WireGuard port 51820, but configurable).
- **Internal endpoints**: Should be resolvable and reachable within the local network (e.g., `192.168.1.10:51820` or `server.local:51820`).
- **Port consistency**: All devices should use the same WireGuard port (default 51820) for consistent configuration generation.

## Addressing guidance

- Each WireGuard network defines a CIDR (for example `192.168.123.0/24`). Devices must receive unique IPs inside that range.
- Gateways that serve roaming clients should reserve stable IPs and expose DNS that maps to their external endpoint.
- Avoid overlapping CIDRs across networks unless you explicitly handle NAT or routing exceptions.

## Key management expectations

- Private keys are encrypted at rest and require the **master password** to decrypt. The password is cached only in memory and never written to disk.
- API keys for device self-service retrieval are hashed and validated with constant-time comparison. Treat raw keys as secrets; rotate them on schedule.
- Device self-service config retrieval does not use the master password. It relies on per-device encrypted envelopes for private keys and any location/network preshared keys; missing envelopes must be refreshed by an administrator.

## Device-to-device connectivity patterns

In mesh topology, devices establish direct tunnels with each other based on several factors:

### Connectivity Examples

**Example 1: Two-location site-to-site mesh**

```
Location A (Data Center)
  - Device A1: internal=10.0.1.10:51820, external=203.0.113.10:51820
  - Device A2: internal=10.0.1.11:51820, external=203.0.113.11:51820

Location B (Branch Office)
  - Device B1: internal=192.168.1.10:51820, external=198.51.100.10:51820
  - Device B2: internal=192.168.1.11:51820, external=198.51.100.11:51820

Connectivity:
  - A1 ↔ A2: Uses internal endpoints (10.0.1.10:51820 ↔ 10.0.1.11:51820)
  - B1 ↔ B2: Uses internal endpoints (192.168.1.10:51820 ↔ 192.168.1.11:51820)
  - A1 ↔ B1: Uses external endpoints (203.0.113.10:51820 ↔ 198.51.100.10:51820)
  - A1 ↔ B2: Uses external endpoints (203.0.113.10:51820 ↔ 198.51.100.11:51820)
```

**Example 2: Road-warrior with single location**

```
Office Location
  - Gateway G1: external=203.0.113.10:51820

Road-warrior devices:
  - Laptop L1: external=dynamic (DNS: laptop.example.com), no internal endpoint
  - Phone P1: external=dynamic (DNS: phone.example.com), no internal endpoint

Connectivity:
  - L1 ↔ G1: Uses external endpoint (203.0.113.10:51820)
  - P1 ↔ G1: Uses external endpoint (203.0.113.10:51820)
  - L1 ↔ P1: Both use external endpoints via their respective DNS names
```

### Network Traffic Flow

- **Same location traffic**: Stays within the local network, using internal endpoints for minimal latency.
- **Cross-location traffic**: Routes over the public internet using external endpoints.
- **Roaming clients**: Always use external endpoints since they lack stable internal connectivity.
- **Failover**: If an internal endpoint is unreachable, traffic can use the external endpoint as fallback (if configured).

### Scalability Considerations

- **Mesh size**: For optimal performance, limit networks to 50-100 devices per network. Larger networks may benefit from hierarchical network designs.
- **Handshake overhead**: Each device maintains WireGuard handshakes with all peers. Network load grows quadratically with device count.
- **Device filtering**: Disabled devices or devices without public keys are excluded from mesh configurations.

## Operational checks before production

- Confirm every network has at least one location and each location has appropriate endpoints configured.
- Verify external endpoints are reachable from the internet (test with `nc -uzv <host> <port>` or similar).
- Validate internal endpoints are reachable within their local networks.
- Verify rate limiting and audit logging are enabled for device config retrieval.
- Validate configs with the lint/export tooling before distributing them to devices.
- Document who controls the master password and how rotation is handled during incidents.
- Test connectivity between devices in different locations before full deployment.
