# WireGuard Mesh Manager — Product Spec

## Personas

- **Platform Admin (primary)**
  - Runs secure networking for multiple sites or tenants.
  - Needs predictable config generation, auditability, and strict control over who can manage or export keys.
- **Site Operator**
  - Manages devices within a specific location.
  - Focused on adding/removing devices, validating endpoints, and ensuring peers stay reachable.
- **Device Maintainer (self-service)**
  - Responsible for an individual device or appliance.
  - Retrieves its own configuration using scoped credentials and follows approved rotation/reset processes.

## Core workflows

- **Create a network**
  - Define network CIDR, optional shared preshared key, and baseline settings (DNS/MTU/keepalive defaults).
  - Add at least one location and ensure invariants are enforced (≥1 location per network).
- **Provision locations and devices**
  - Create locations under a network and register devices with internal/external endpoints and WireGuard IPs.
  - Validate CIDR membership, endpoint formats, and uniqueness of addresses and device names.
- **Secure key management**
  - Generate or import device keypairs with encryption-at-rest using a master password cache.
  - Rotate/re-encrypt keys and revoke API keys with audit trails; never expose private keys in logs or UI.
- **Config generation and export**
  - Produce deterministic device configs using location-aware endpoint selection and optional network-level PSK.
  - Export per-device or full-network bundles with redaction of sensitive fields where appropriate.
- **Device self-service retrieval**
  - Allow devices to fetch their own config using API keys plus IP allowlists and rate limiting.
  - Record audit events for successful/failed retrieval attempts without leaking secrets.
- **Operational governance**
  - Monitor health/readiness, view audit events, and apply policy toggles (trusted proxy behavior, CORS, rate limits).
  - Perform backups/restores of encrypted state and migrate data between instances safely.

## Non-goals

- Running the WireGuard data plane itself (no embedded VPN gateway/runtime).
- Providing consumer VPN-style account management or traffic analytics/inspection.
- Automatic topology discovery or intent-based networking beyond declared networks/locations/devices.
- Managing non-WireGuard VPN protocols.
