# Mesh Topology Architecture

This document describes the mesh topology architecture used by the WireGuard Mesh Manager (WMM). WMM uses a full mesh topology where all devices connect directly to each other without a central WireGuard server.

## Overview

### What is Mesh Topology?

In mesh topology, every device in a network can connect directly to every other device, forming a peer-to-peer network. Unlike traditional hub-and-spoke architectures where all clients connect through a central server, mesh networks provide:

- **No single point of failure**: If one device goes down, others can still communicate
- **Optimal routing**: Traffic takes the most direct path between devices
- **Simplified deployment**: No need to manage a central WireGuard server
- **Scalability**: Easy to add new devices without reconfiguring existing infrastructure

### How WMM Implements Mesh Topology

WMM generates complete WireGuard configurations for each device that include all other devices in the network as peers. The key implementation features are:

1. **Full peer mesh**: Each device's configuration includes all other enabled devices in the network
2. **Intelligent endpoint selection**: Automatically chooses the optimal endpoint (internal vs external) based on device locations
3. **Device-level endpoints**: Each device has both internal and external endpoint configuration
4. **Centralized configuration management**: WMM generates and distributes configurations but doesn't participate in the WireGuard network itself

### Architecture Diagram

```
                            [WMM Backend Service]
                                    |
                                    | HTTP API (Config Generation)
                                    |
                    +---------------+---------------+
                    |                               |
            [Device A]                    [Device B]                 [Device C]
                |                               |                             |
                |---<WireGuard Tunnel>--------|-----<WireGuard Tunnel>------|
                |                               |                             |
                |---------<WireGuard Tunnel>---------------------------------|

- Each device runs WireGuard independently
- Devices establish direct tunnels with all peers
- WMM generates configurations but does not run WireGuard
- Traffic flows directly between devices
```

## Core Concepts

### 1. Network, Locations, and Devices

#### WireGuardNetwork
- Defines the IP network/CIDR (e.g., `192.168.123.0/24`) used by all devices
- Contains network-level settings (DNS, MTU, persistent keepalive)
- May define an optional network-level shared key (PSK)
- Has one or more Locations

#### Location
- Represents a physical or logical grouping of devices
- Examples: "Data Center East", "Branch Office", "Cloud Region"
- Has an external endpoint (publicly reachable)
- Has an internal endpoint (reachable within the local network)
- Contains zero or more Devices

#### Device
- Represents a single WireGuard peer (server, router, laptop, etc.)
- Has a unique WireGuard IP within the network CIDR
- Has a public key and an encrypted private key
- Has device-level endpoints (internal and external)
- Belongs to exactly one Location (and therefore one WireGuardNetwork)

### 2. Endpoint Selection Rules

WMM automatically selects the appropriate endpoint for each peer based on location relationships:

#### Same Location: Use Internal Endpoint
When two devices are in the same location:
- Use the peer's **internal endpoint**
- Keeps traffic within the local network segment
- Reduces latency and avoids hairpinning
- Example: Two servers in the same data center communicate over private IP

#### Different Locations: Use External Endpoint
When two devices are in different locations:
- Use the peer's **external endpoint**
- Enables connectivity across network boundaries
- Works over public internet or VPN
- Example: Data center server connects to branch office gateway

#### Fallback Behavior
If a device has no internal endpoint configured:
- Use the external endpoint even for same-location peers
- Ensures connectivity is always possible

### 3. Configuration Generation Process

#### Step-by-Step Process

1. **Network Analysis**
   - Identify all devices in the network
   - Filter out disabled devices
   - Identify devices without public keys (excluded from mesh)

2. **Peer Selection**
   - Include all enabled devices with public keys
   - Exclude the device being configured (no self-peering)
   - Sort peers by IP address for deterministic output

3. **Endpoint Determination**
   - For each peer, check if it's in the same location
   - Same location → use internal endpoint
   - Different location → use external endpoint
   - Handle missing endpoints with fallback logic

4. **Configuration Assembly**
   - Build interface section with device's private key and IP
   - Add network-level settings (DNS, MTU, persistent keepalive)
   - Add peer section for each peer with:
     - Public key
     - Allowed IPs (peer's WireGuard IP)
     - Endpoint (internal or external)
     - Preshared key (if configured)
     - Persistent keepalive (if configured)

5. **Output Generation**
   - Generate configuration in requested format (wg, json, mobile)
   - Ensure deterministic ordering for stable diffs
   - Return complete configuration to requester

#### Configuration Structure

**WireGuard Format (.conf):**
```ini
[Interface]
PrivateKey = <device_private_key>
Address = <device_wireguard_ip>/<cidr_prefix>
DNS = 8.8.8.8,8.8.4.4
MTU = 1420

[Peer]
PublicKey = <peer1_public_key>
AllowedIPs = <peer1_wireguard_ip>/32
Endpoint = <peer1_endpoint>
PresharedKey = <optional_psk>
PersistentKeepalive = 25

[Peer]
PublicKey = <peer2_public_key>
AllowedIPs = <peer2_wireguard_ip>/32
Endpoint = <peer2_endpoint>
PresharedKey = <optional_psk>
PersistentKeepalive = 25
```

**JSON Format:**
```json
{
  "configuration": {
    "interface": {
      "private_key": "...",
      "address": "10.0.0.2/24",
      "dns": "8.8.8.8,8.8.4.4",
      "mtu": 1420
    },
    "peers": [
      {
        "public_key": "...",
        "allowed_ips": "10.0.0.3/32",
        "endpoint": "peer1.internal:51820",
        "preshared_key": null,
        "persistent_keepalive": 25
      },
      {
        "public_key": "...",
        "allowed_ips": "10.0.0.4/32",
        "endpoint": "peer2.example.com:51820",
        "preshared_key": "...",
        "persistent_keepalive": 25
      }
    ]
  }
}
```

## Deployment Patterns

### Pattern 1: Site-to-Site Mesh

**Use Case:** Multiple offices or data centers need secure connectivity

**Configuration:**
- Each site is a Location
- Each site has multiple Devices (servers, routers)
- Internal endpoints for local traffic
- External endpoints for cross-site traffic

**Example:**
```
Location: Data Center East (10.1.1.0/24)
  - Device A1: internal=10.1.1.10:51820, external=203.0.113.10:51820
  - Device A2: internal=10.1.1.11:51820, external=203.0.113.11:51820

Location: Data Center West (10.2.1.0/24)
  - Device B1: internal=10.2.1.10:51820, external=198.51.100.10:51820
  - Device B2: internal=10.2.1.11:51820, external=198.51.100.11:51820

Connectivity:
  - A1 ↔ A2: Internal (10.1.1.10 ↔ 10.1.1.11) - local traffic
  - B1 ↔ B2: Internal (10.2.1.10 ↔ 10.2.1.11) - local traffic
  - A1 ↔ B1: External (203.0.113.10 ↔ 198.51.100.10) - cross-site
  - A1 ↔ B2: External (203.0.113.10 ↔ 198.51.100.11) - cross-site
```

### Pattern 2: Road-Warrior Access

**Use Case:** Roaming users (laptops, mobile devices) need secure access to company resources

**Configuration:**
- Office is a Location with stable external endpoint
- Roaming devices are individual Devices in their own Locations
- Roaming devices use dynamic DNS for external endpoints
- No internal endpoints for roaming devices

**Example:**
```
Location: Main Office
  - Gateway G1: external=vpn.company.com:51820, internal=10.1.1.1:51820

Location: User Laptop (dynamic)
  - Laptop L1: external=laptop.dyn.company.com:51820, internal=None

Location: User Phone (dynamic)
  - Phone P1: external=phone.dyn.company.com:51820, internal=None

Connectivity:
  - L1 ↔ G1: External endpoints (both different locations)
  - P1 ↔ G1: External endpoints (both different locations)
  - L1 ↔ P1: External endpoints (both different locations)
```

### Pattern 3: Hybrid Mesh

**Use Case:** Mix of fixed sites and roaming users

**Configuration:**
- Multiple Locations for fixed sites
- Individual Locations for each roaming user
- Intelligent endpoint selection handles all cases automatically

**Example:**
```
Location: HQ (10.1.1.0/24)
  - HQ-Server-1: internal=10.1.1.10:51820, external=203.0.113.10:51820
  - HQ-Server-2: internal=10.1.1.11:51820, external=203.0.113.11:51820

Location: Branch (10.2.1.0/24)
  - Branch-Gateway: internal=10.2.1.10:51820, external=198.51.100.10:51820

Location: Remote-User-1 (dynamic)
  - Laptop: external=user1.dyn.company.com:51820, internal=None

Connectivity:
  - HQ-Server-1 ↔ HQ-Server-2: Internal (same location)
  - HQ-Server-1 ↔ Branch-Gateway: External (different locations)
  - HQ-Server-1 ↔ Laptop: External (different locations)
  - Branch-Gateway ↔ Laptop: External (different locations)
```

## Implementation Details

### Backend Service

#### DeviceConfigService

The `DeviceConfigService` class in `backend/app/services/device_config.py` is responsible for generating mesh topology configurations.

**Key Methods:**

- `generate_device_config()`: Main entry point for configuration generation
- `_generate_peer_configs()`: Generates peer configurations for mesh topology
- `_get_device_endpoint()`: Selects endpoint based on location rules
- `_should_include_peer()`: Determines if a peer should be included
- `_get_preshared_key_for_pair()`: Retrieves preshared key for peer pair

**Endpoint Selection Logic:**

```python
def _get_device_endpoint(self, device: Device, peer_device: Device) -> str | None:
    """Get the endpoint for a peer device based on location rules.

    - Same location: use peer's internal endpoint
    - Different location: use peer's external endpoint
    """
    same_location = (
        device.location
        and peer_device.location
        and device.location.id == peer_device.location.id
    )

    if same_location:
        # Use internal endpoint for same location
        if peer_device.internal_endpoint:
            return peer_device.internal_endpoint
        return peer_device.external_endpoint  # Fallback
    else:
        # Use external endpoint for different locations
        return peer_device.external_endpoint
```

### Database Schema

The database models support mesh topology through the following relationships:

**WireGuardNetwork** → **Location** → **Device**

- Network has many Locations
- Location has many Devices
- Device belongs to exactly one Location (and one Network)
- Device stores both `internal_endpoint` and `external_endpoint`

### API Endpoints

#### Device Self-Service Endpoints

- `GET /api/devices/{device_id}/config` - Get device configuration (JSON)
- `GET /api/devices/{device_id}/config/wg` - Get device configuration (WireGuard format)

#### Admin Endpoints

- `GET /api/devices/admin/{device_id}/config` - Get any device's configuration (admin)
- `GET /api/devices/admin/{device_id}/config/wg` - Get any device's configuration (admin, WireGuard format)

## Benefits and Trade-offs

### Benefits

1. **No Single Point of Failure**
   - If one device fails, others can still communicate
   - No central server that can take down the entire network
   - Graceful degradation of network capacity

2. **Optimal Routing**
   - Traffic takes the most direct path between devices
   - Reduced latency compared to hub-and-spoke through a central server
   - Better performance for cross-location traffic

3. **Simplified Deployment**
   - No need to deploy and maintain a central WireGuard server
   - WMM is a management tool, not a network participant
   - Easier to scale by adding devices

4. **Flexibility**
   - Easy to add new devices without reconfiguring existing infrastructure
   - Supports mixed environments (servers, laptops, mobile devices)
   - Works across different network types (local networks, internet, cloud)

5. **Security**
   - Direct device-to-device encryption via WireGuard
   - No intermediate devices that could intercept traffic
   - Each device has its own encrypted private key

### Trade-offs

1. **Configuration Complexity**
   - Each device must know about all other devices
   - Configuration files grow with network size (N-1 peers per device)
   - More complex to debug connectivity issues

2. **Mesh Scaling Limits**
   - For optimal performance, limit to 50-100 devices per network
   - WireGuard handshake overhead grows quadratically with device count
   - Larger networks may benefit from hierarchical designs

3. **Endpoint Management**
   - Each device needs both internal and external endpoints configured
   - Requires NAT/firewall configuration for external connectivity
   - Dynamic IPs require DNS updates or DDNS

4. **Network Monitoring**
   - More difficult to monitor overall network health
   - Each device needs individual monitoring
   - No central point to aggregate connection status

## Scalability Considerations

### Network Size Recommendations

- **Small networks (1-10 devices)**: No special considerations
- **Medium networks (10-50 devices)**: Monitor performance and handshake overhead
- **Large networks (50-100 devices)**: Consider hierarchical design or segmentation
- **Very large networks (100+ devices)**: Split into multiple networks or use hub-and-spoke for some connections

### Performance Factors

**WireGuard Handshakes:**
- Each device maintains handshakes with all peers
- Handshakes are lightweight but not zero-cost
- Handshake overhead grows quadratically with device count

**Configuration Size:**
- Each device's config includes all peers
- Config file size grows linearly with peer count
- Large configs may slow device startup and rekeying

**Network Traffic:**
- Each device sends keepalives to all peers
- Keepalive traffic grows quadratically with device count
- Consider adjusting persistent keepalive for large networks

### Optimization Strategies

1. **Disable Unnecessary Peers**
   - Disable devices that don't need to participate in mesh
   - Use device enable/disable flag to control participation
   - Consider using separate networks for different use cases

2. **Adjust Keepalive Intervals**
   - Longer intervals reduce traffic but increase latency
   - Default 25 seconds is a good balance
   - Adjust based on network conditions and NAT timeouts

3. **Use Network Segmentation**
   - Split large networks into multiple smaller networks
   - Use gateways to connect networks if needed
   - Reduces mesh size per network

4. **Optimize Endpoint Selection**
   - Ensure internal endpoints are used when possible
   - Reduces internet traffic for local communication
   - Improves latency and reduces costs

## Security Considerations

### Key Management

- **Private Keys**: Encrypted at rest with master password
- **Public Keys**: Stored in database, used for configuration generation
- **Preshared Keys**: Optional, can be device-level or network-level
- **Master Password**: Cached in memory only, never written to disk

### Access Control

- **API Keys**: Device-specific, hashed, constant-time comparison
- **IP Allowlists**: Restrict device config retrieval by source IP
- **Master Session**: Admin access requires master password unlock
- **Audit Logging**: All configuration retrievals are logged

### Network Security

- **Endpoint Reachability**: External endpoints must be accessible from internet
- **Firewall Rules**: Allow UDP traffic on WireGuard port (default 51820)
- **NAT Traversal**: Devices behind NAT need port forwarding or hole punching
- **DNS Integrity**: External DNS names must resolve correctly for all devices

### Configuration Security

- **No Secrets in URLs**: Configuration retrieval uses POST body or headers
- **Rate Limiting**: Prevents brute force attacks on API keys
- **Cache Control**: Disallows caching of sensitive configuration data
- **Content Security**: Enforces content type to prevent MIME sniffing

## Troubleshooting

### Common Issues

#### 1. Devices Cannot Connect

**Symptoms:**
- `wg show` shows no handshake
- Connection timeouts
- Peers appear in config but no traffic

**Possible Causes:**
- Endpoint is unreachable (firewall, NAT, incorrect address)
- Port is not open or forwarded
- Device is behind NAT without port forwarding

**Solutions:**
- Verify endpoint is reachable: `nc -uzv <host> <port>`
- Check firewall rules: `sudo ufw status` or `iptables -L`
- Test connectivity from remote network
- Verify port forwarding configuration
- Check NAT traversal settings

#### 2. Peers Using Wrong Endpoint

**Symptoms:**
- Traffic going through external endpoint for same-location devices
- Latency higher than expected
- Hairpinning traffic

**Possible Causes:**
- Device missing internal endpoint
- Location configuration incorrect
- Devices assigned to wrong location

**Solutions:**
- Configure internal endpoint on devices
- Verify location assignments are correct
- Check endpoint selection logic in device config
- Review WMM configuration generation logs

#### 3. Configuration Too Large

**Symptoms:**
- Slow device startup
- High memory usage
- Long rekeying times

**Possible Causes:**
- Too many peers in mesh
- Network exceeds recommended size

**Solutions:**
- Split network into smaller segments
- Disable unnecessary devices
- Consider hierarchical network design
- Remove unused devices

#### 4. Intermittent Connectivity

**Symptoms:**
- Peers connect then disconnect
- Frequent handshake failures
- Connection drops

**Possible Causes:**
- Network instability
- NAT timeout
- Keepalive interval too long
- DNS issues

**Solutions:**
- Adjust persistent keepalive interval
- Use static IPs instead of DNS for endpoints
- Verify network stability
- Check NAT/firewall logs
- Test with longer keepalive interval

### Debugging Tools

**WireGuard Tools:**
- `wg show` - Show current WireGuard status
- `wg showconf <interface>` - Show current configuration
- `tcpdump -i <interface> -n port 51820` - Capture WireGuard traffic

**Network Tools:**
- `nc -uzv <host> <port>` - Test UDP connectivity
- `traceroute <host>` - Trace network path
- `mtr <host>` - Real-time network diagnostics
- `dig <hostname>` - Verify DNS resolution

**WMM Tools:**
- WMM admin UI - View device configurations
- `/api/config/lint` - Validate network configuration
- Audit logs - View configuration retrieval history

## Best Practices

### Network Design

1. **Plan CIDR Allocation Carefully**
   - Use /24 networks for most use cases (256 addresses)
   - Reserve space for expansion
   - Avoid overlapping CIDRs across networks

2. **Organize Locations Logically**
   - Group devices by physical location
   - Group devices by network segment
   - Keep similar devices together (e.g., all office servers in one location)

3. **Use Descriptive Names**
   - Clear device names help debugging
   - Include location and purpose in names
   - Example: "dc-east-web-01", "branch-west-gw"

### Endpoint Configuration

1. **Always Configure Internal Endpoints for Fixed Devices**
   - Reduces internet traffic
   - Improves latency
   - Reduces costs

2. **Use DNS for External Endpoints**
   - Easier to update than IP addresses
   - Supports dynamic IP addresses
   - Use DDNS for devices with changing IPs

3. **Use Standard WireGuard Port**
   - Default is 51820
   - Consistent across all devices
   - Simplifies firewall rules

### Security

1. **Rotate API Keys Regularly**
   - Rotate device API keys periodically
   - Revoke keys for compromised devices
   - Use strong API key generation

2. **Use Preshared Keys**
   - Add layer of security with PSKs
   - Use network-level PSK for consistency
   - Use device-level PSKs for specific security needs

3. **Audit Configuration Access**
   - Monitor audit logs for suspicious activity
   - Review API key usage patterns
   - Investigate failed authentication attempts

### Monitoring

1. **Monitor Device Health**
   - Track uptime and connectivity
   - Monitor handshake success rates
   - Alert on device failures

2. **Monitor Network Performance**
   - Track latency between peers
   - Monitor traffic volumes
   - Identify bottlenecks

3. **Regular Configuration Reviews**
   - Validate configurations with lint tool
   - Review endpoint reachability
   - Check for disabled devices

## Comparison with Hub-and-Spoke

| Aspect | Mesh Topology | Hub-and-Spoke |
|--------|--------------|---------------|
| **Server Required** | No central server | Central WireGuard server required |
| **Point of Failure** | None (peer-to-peer) | Central server is SPOF |
| **Routing** | Direct peer-to-peer | Through central server |
| **Scalability** | Limited by mesh size | Limited by server capacity |
| **Configuration** | Each device has N-1 peers | Each device has 1 peer (server) |
| **Deployment** | Decentralized | Centralized |
| **Complexity** | Higher (more peers) | Lower (simple configuration) |
| **Performance** | Optimal (direct paths) | Suboptimal (through server) |
| **Management** | Requires WMM for config generation | Can be managed manually |

## Future Enhancements

Potential areas for future development:

1. **Hierarchical Mesh**
   - Support for multi-level mesh networks
   - Gateway devices between sub-meshes
   - Improved scalability for large networks

2. **Dynamic Peer Discovery**
   - Automatic discovery of new devices
   - Integration with service discovery
   - Zero-touch provisioning

3. **Smart Endpoint Selection**
   - Latency-based endpoint selection
   - Automatic failover between endpoints
   - Quality of Service (QoS) aware routing

4. **Mesh Monitoring**
   - Centralized mesh health monitoring
   - Real-time topology visualization
   - Automated issue detection and alerting

5. **Advanced Security**
   - Certificate-based authentication
   - Zero-trust network access
   - Integration with SSO systems

## Related Documentation

- [WireGuard Assumptions](WIREGUARD_ASSUMPTIONS.md) - WireGuard configuration expectations and examples
- [Deployment Topology](DEPLOYMENT_TOPOLOGY.md) - Production deployment considerations
- [Device Config API](DEVICE_CONFIG_API.md) - API documentation for configuration retrieval
- [Production Runbook](PRODUCTION_RUNBOOK.md) - Operational procedures and troubleshooting
- [Threat Model](THREAT_MODEL.md) - Security assumptions and controls

## Version History

- **v1.0** (2025-12-30): Initial mesh topology architecture documentation
