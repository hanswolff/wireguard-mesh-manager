# API Stability Policy

## Overview

The WireGuard Mesh Manager API is intentionally **unversioned**. We do not use versioned paths or headers and do not plan to introduce `/v1`, `/v2`, or similar schemes.

## Endpoint Policy

- **Base URL:** `https://api.example.com/api`
- **Development:** `http://localhost:8000/api`
- All endpoints live under `/api/*` without a version prefix.

## Change Management

- Breaking changes are allowed, but must be coordinated with client updates.
- Release notes must call out request/response shape changes.
- There is **no deprecation window** for older clients; rollouts assume clients move in lockstep.

## Compatibility Expectations

- New optional fields are preferred for additive changes.
- Removing or changing required fields is considered breaking.
- Authentication and authorization changes require explicit client updates.

## Device Configuration Retrieval

```
GET  /api/devices/{device_id}/config
GET  /api/devices/{device_id}/config?format=json
GET  /api/devices/{device_id}/config?format=mobile&platform=ios
```

## Error Handling

All API errors follow a consistent structure:

```json
{
  "error": {
    "code": "DEVICE_NOT_FOUND",
    "message": "Device with ID '123' not found",
    "details": {
      "device_id": "123",
      "network_id": "456"
    },
    "timestamp": "2024-01-01T12:00:00Z",
    "request_id": "req_abc123"
  }
}
```
