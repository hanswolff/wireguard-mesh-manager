# WireGuard Mesh Manager — Threat Model

## Scope and goals

- Protect WireGuard private keys, API keys, and generated configs at rest and in transit.
- Preserve integrity of network topology metadata (networks, locations, devices, allowlists).
- Ensure only authorized administrators can mutate configuration or export secrets.
- Let devices retrieve only their own configs with least privilege and auditable access.

## Roles and trust boundaries

- **Admins (platform + site operators):** Trusted to manage topology, keys, and policy; authenticated via the master password and a master session token. The password is never persisted and must be re-supplied on restart or after lock.
- **Devices (self-service clients):** Only trusted to retrieve their own configuration using scoped API keys and source-IP allowlists. They cannot create, update, or delete topology, and cannot see other device configs.
- **Infrastructure operators:** Trusted to provision servers and storage but should not access decrypted key material. Secrets at rest remain encrypted; master password is required to decrypt.

## Assets

- Encrypted private keys for devices and optional network preshared key.
- Device API keys and retrieval allowlists.
- Network/location/device metadata and audit logs.
- Generated WireGuard configs (per-device and network bundles).

## Attacker capabilities and assumptions

- **Remote network attacker:** Can send arbitrary requests to the admin API and device retrieval endpoints. Mitigations: strict authZ/authN (master sessions + device API keys), IP allowlists for device retrieval, rate limiting, request body limits, and constant-time API key comparison.
- **Compromised device:** Possesses its own API key and decrypted private key; cannot access other devices if allowlists and scoping are enforced. Revocation and rotation must be supported to contain impact.
- **Curious infrastructure admin / DB dump:** May read the database or backups but does not have the master password. Private keys remain encrypted with a strong KDF + AEAD; API keys should be stored hashed.
- **Malicious insider with master session:** Can perform destructive actions; audit logging and role separation help with detection. Sensitive operations (decrypt/export) require the master password and should be rate-limited with clear UX.
- **MITM on device retrieval path:** Without TLS termination at a trusted proxy, configs and API keys could be exposed. Deployment must enforce TLS, HSTS, and disable caching for sensitive endpoints.
- **Log scraping / crash dumps:** Logs and traces must exclude private keys, master password, and raw API keys; use redaction helpers and avoid storing secrets in process dumps.

## Security assumptions

- TLS terminates at a trusted proxy/load balancer that forwards correct client IPs when allowlists are enabled (with clear trusted-proxy configuration).
- Master password is entered by a trusted admin at startup/unlock and cached only in-memory with explicit TTL/lock controls; never written to disk or environment variables.
- Administrators use hardened endpoints (MFA, least-privilege OS accounts) and rotate credentials regularly.
- Devices can protect API keys at rest (e.g., filesystem permissions or hardware-backed storage) and honor rotation procedures.
- Database and backup storage enforce OS-level access controls; encrypted backups use strong keys separate from the master password.

## Out of scope / non-goals

- Protecting against a fully compromised host where memory can be read (master password and decrypted keys are exposed in this scenario).
- Guaranteeing device identity beyond possession of its API key and allowed source IP; additional attestation is not provided.
- Running WireGuard data plane or enforcing traffic policies beyond configuration generation.
