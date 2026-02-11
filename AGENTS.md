# WireGuard Mesh Manager (WMM)

This repository is a secret-management and configuration-deployment tool for WireGuard-based infrastructure.

## Target architecture

- **Frontend:** Next.js 16 (App Router), TailwindCSS v3.4.0, TypeScript, server actions for management flows where appropriate (use pnpm package manager).
  - **Important:** The frontend uses TailwindCSS v3.4.0. Do not upgrade to v4.0 as the styling syntax is incompatible.
- **Backend:** Python API service (prefer FastAPI), responsible for auth, key management, encryption, and config generation (use uv package manager).
- **Database:** SQLite3 (initially), with schema migrations; stores WireGuard networks/locations/devices and encrypted private keys.

## Project status

- WMM is implemented and operational with mesh-topology config generation, master-session admin access, device self-service retrieval, and audit/security controls.
- Treat current runtime behavior as baseline: preserve existing security and compatibility expectations unless a task explicitly requires change.

## Canonical documentation (source of truth)

- Product and workflows: `docs/PRODUCT_SPEC.md`
- Threat model and assumptions: `docs/THREAT_MODEL.md`
- Mesh topology and endpoint selection: `docs/MESH_TOPOLOGY_ARCHITECTURE.md`
- API stability policy: `docs/api-versioning-policy.md`
- Frontend architecture decisions: `docs/FRONTEND_ARCHITECTURE.md`
- Test strategy and coverage goals: `docs/test-strategy.md`
- Operations and incident procedures: `docs/PRODUCTION_RUNBOOK.md`

## Domain model (core invariants)

- **WireGuardNetwork**
  - Defines an IP network/CIDR (e.g. `192.168.123.0/24`) that all devices in the network use for WireGuard addresses.
  - Has **≥ 1** Location.
  - May define an optional **network-level shared key** (treated as an optional PSK applied consistently during config generation).
- **Location**
  - Belongs to one WireGuardNetwork.
  - Has **≥ 0** Devices.
  - Has an **external endpoint** (hostname or IP address only, no port). The port is determined by device configuration, not location.
  - May have an optional **internal endpoint** (`host/ip:port`) for same-location device communication.
- **Device**
  - Belongs to one Location (and therefore one WireGuardNetwork).
  - Has an **internal endpoint** (`host/ip:port`) and an **external endpoint** (`host/ip:port`).
  - Has a **public key** and an **encrypted private key** and a name / description.

## Non-negotiable architecture invariants

- WMM generates and manages WireGuard configs but does not run the WireGuard data plane.
- Admin access uses master-session and master-password unlock semantics; do not reintroduce user-login auth flows unless explicitly requested.
- API endpoints are unversioned under `/api` (no `/v1`, `/v2`, or versioned headers).
- TailwindCSS must stay on `v3.4.x`; do not migrate to `v4` unless explicitly requested.

## Data and config invariants

- A WireGuardNetwork must have at least one Location (enforced at API/service boundaries).
- Devices belong to exactly one Location and one WireGuardNetwork.
- Device endpoints are represented as split host/port fields in storage and validation.
- Config generation and exports must remain deterministic in ordering and output.
- Do not reintroduce removed network server-key/listen-port config model without explicit direction.

## Configuration generation rules

- Generate complete WireGuard configs per **network** and per **device**.
- When generating a device config, each peer’s `Endpoint` is chosen based on relative location:
  - **Same location:** use the peer’s **internal endpoint**
  - **Different location:** use the peer’s **external endpoint**
- If the network has a shared key, apply it consistently as the peer `PresharedKey` during generation (do not invent per-peer variations unless explicitly modeled).

## Secret handling requirements

- Private keys are **encrypted at rest** using a **master password**.
- The master password must be:
  - required for sensitive operations (manage devices, decrypt keys, export configs)
  - **cached in-memory only** for the lifetime of the backend process/session (never written to disk)
  - excluded from logs, traces, and error messages

## Recommended design: per-device "envelope" key tied to API key

**Core idea**

Each device has a data-encryption key (DEK) used to encrypt its private key.

The DEK is stored twice:

- Encrypted with the master password (for admin and rotation).
- Encrypted with a key derived from the device's API key (for device self-service).

When a device requests config, the API key is verified and used to decrypt the DEK; the DEK decrypts the private key.

**Benefits**

- Devices can retrieve their configs without the master password being present.
- Admins retain full control via master password and can rotate API keys without re-encrypting private keys.
- Compromise of a single device's API key cannot expose other devices' private keys.

## Device self-service config retrieval

- Devices must be able to request their own generated config from the backend.
- Access must be gated by explicit authentication/authorization rules such as:
  - API keys with constant-time comparison
  - request-source IP allowlists (CIDR ranges) per device and/or per network
  - rate limiting and audit logging (never log secrets)
- **Performance:** API key validation must be fast and not become a bottleneck. Use efficient lookups (e.g., indexed DB queries or in-memory caching) to ensure validation completes in sub-millisecond time.

## Quality and security bar

- Prefer simple, explicit designs; keep modules small and responsibilities clear.
- Validate all inputs at the boundary (API layer); never trust client-provided IDs or endpoints.
- Avoid leaking sensitive material in logs/test snapshots; use redaction helpers.
- Use parameterized DB access (ORM or prepared statements) and enforce referential integrity.
- Add tests for:
  - config generation (endpoint selection rules, AllowedIPs, PSK behavior)
  - encryption/decryption (wrong password, rotation/migration behavior)
  - authZ/authN (API keys, IP allowlists, access boundaries)
  - API integration (happy-path + common failure modes)
- Do not use GitHub workflow scripts.
- Rate-limit backend behavior is considered intentionally degradable; a graceful fallback to slower or no-op enforcement is a
  feature, not a bug.
- API endpoints are **unversioned**; do not introduce `/v1`, `/v2`, or versioned headers.

## Work tracking

- Track new work in the issue tracker and/or scoped implementation documents under `docs/`.
