# Device Config Retrieval API Documentation

This document describes the API endpoints for device configuration retrieval in the WireGuard Mesh Manager.

## Overview

The WireGuard Mesh Manager provides two sets of endpoints for device configuration retrieval:

1. **Device self-service endpoints** - Used by devices to retrieve their own configurations
2. **Admin endpoints** - Used by administrators to retrieve device configurations

All device config retrieval requires authentication and authorization.

## Authentication

### Device Self-Service Authentication

Devices authenticate using:

- **API Key**: A device-specific API key (hashed in database, shown once during creation)
- **IP Allowlist**: Source IP must be in the device's configured allowlist
- **Method**: API key provided via `Authorization: Bearer <api-key>` header

Self-service retrieval never uses the master password. Device private keys and any
location/network preshared keys are decrypted using the API-key-derived envelope.
If a location/network preshared key exists but a device-specific encrypted copy is
missing (for example after a preshared key update), the request will be rejected
until an administrator refreshes the device's encrypted key cache.

### Admin Authentication

Administrators authenticate using:

- **Master session token**: Returned by `POST /master-password/unlock` and passed as `Authorization: Master <token>`
- **Master Password**: Must be unlocked to access device configurations

Master sessions are in-memory only and expire with the master password cache TTL
and idle timeout. Use `/master-password/status` to inspect TTL, `/master-password/extend-ttl`
to extend it, and `/master-password/refresh-access` as a heartbeat.

## Base URLs

- **Self-hosted deployment**: `https://<your-domain>/api`
- **Development**: `http://localhost:8000/api`

## Device Self-Service Endpoints

### 1. Get Device Configuration (JSON)

```http
GET /api/devices/{device_id}/config
```

Retrieves device configuration in JSON format.

#### Parameters

| Name      | Type   | In    | Description                                                               |
| --------- | ------ | ----- | ------------------------------------------------------------------------- |
| device_id | string | path  | UUID of the device                                                        |
| format    | string | query | Config format: `wg`, `json`, `mobile` (default: `wg`)                     |
| platform  | string | query | Mobile platform: `ios`, `android`, `windows`, `macos`, `linux` (optional) |

#### Headers

| Name         | Type   | Description                          |
| ------------ | ------ | ------------------------------------ |
| Authorization | string | `Bearer <device-api-key>`           |
| Content-Type | string | `application/json`                   |

#### Response (200 OK)

```json
{
  "device_id": "123e4567-e89b-12d3-a456-426614174000",
  "device_name": "iPhone 15",
  "network_name": "Company VPN",
  "configuration": {
    "interface": {
      "private_key": "abc123...", # pragma: allowlist secret
      "address": "10.0.0.2/24",
      "dns": "8.8.8.8,8.8.4.4",
      "mtu": 1420
    },
    "peer": {
      "public_key": "def456...", # pragma: allowlist secret
      "allowed_ips": "0.0.0.0/0",
      "endpoint": "vpn.example.com:51820",
      "persistent_keepalive": 25,
      "preshared_key": null
    }
  },
  "format": "json",
  "created_at": "2024-01-01T12:00:00Z"
}
```

#### Error Responses

- **401 Unauthorized**: Invalid or missing API key
- **403 Forbidden**: IP not in allowlist
- **404 Not Found**: Device not found or disabled
- **409 Conflict**: Device configuration unavailable (missing preshared key cache)
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: Server error

#### Example Request

```bash
curl -X GET \
  "https://<your-domain>/api/devices/123e4567-e89b-12d3-a456-426614174000/config?format=json" \
  -H "Authorization: Bearer wg-device-api-key-12345" \
  -H "Content-Type: application/json"
```

### 2. Get Device Configuration (WireGuard .conf format)

```http
GET /api/devices/{device_id}/config/wg
```

Retrieves device configuration in standard WireGuard .conf format.

#### Parameters

| Name      | Type   | In   | Description        |
| --------- | ------ | ---- | ------------------ |
| device_id | string | path | UUID of the device |

#### Headers

| Name          | Type   | Description                |
| ------------- | ------ | -------------------------- |
| Authorization | string | `Bearer <device-api-key>`  |

#### Response (200 OK)

Returns plain text WireGuard configuration with `Content-Type: text/plain`.

```ini
[Interface]
PrivateKey = abc123...
Address = 10.0.0.2/24
DNS = 8.8.8.8,8.8.4.4
MTU = 1420

[Peer]
PublicKey = def456...
AllowedIPs = 0.0.0.0/0
Endpoint = vpn.example.com:51820
PersistentKeepalive = 25
```

#### Response Headers

| Name                | Description                                    |
| ------------------- | ---------------------------------------------- |
| Content-Disposition | `attachment; filename="Device_Name_wg0.conf"`  |
| Content-Type        | `text/plain; charset=utf-8`                    |
| Cache-Control       | `no-store, no-cache, must-revalidate, private` |

#### Example Request

```bash
curl -X GET \
  "https://<your-domain>/api/devices/123e4567-e89b-12d3-a456-426614174000/config/wg" \
  -H "Authorization: Bearer wg-device-api-key-12345" \
  -o wg0.conf
```

## Admin Endpoints

Admin endpoints require a master session token and unlocked master password.

### 1. Get Device Configuration (Admin)

```http
GET /api/devices/admin/{device_id}/config
```

Retrieves device configuration as an administrator.

#### Parameters

| Name      | Type   | In    | Description                                           |
| --------- | ------ | ----- | ----------------------------------------------------- |
| device_id | string | path  | UUID of the device                                    |
| format    | string | query | Config format: `wg`, `json`, `mobile` (default: `wg`) |
| platform  | string | query | Mobile platform (optional)                            |

#### Authentication

- `Authorization: Master <token>` header
- Master password must be unlocked

#### Response (200 OK)

Same format as device self-service endpoint.

### 2. Get Device Configuration (Admin, .conf format)

```http
GET /api/devices/admin/{device_id}/config/wg
```

Retrieves device configuration as plain text for admin use.

#### Error Responses

- **401 Unauthorized**: Master session missing or invalid
- **423 Locked**: Master password not unlocked
- **404 Not Found**: Device not found

## Mobile Platform Configurations

When `format=mobile` and `platform` is specified, the response is optimized for mobile clients:

### iOS Example

```json
{
  "device_id": "123e4567-e89b-12d3-a456-426614174000",
  "device_name": "iPhone 15",
  "network_name": "Company VPN",
  "configuration": {
    "name": "Company VPN",
    "addresses": ["10.0.0.2/24"],
    "dns": ["8.8.8.8", "8.8.4.4"],
    "mtu": 1420,
    "public_key": "def456...",
    "allowed_ips": ["0.0.0.0/0"],
    "endpoint": "vpn.example.com:51820",
    "persistent_keepalive": 25
  },
  "format": "mobile",
  "created_at": "2024-01-01T12:00:00Z"
}
```

## Configuration Formats

### JSON Format (`format=json`)

- Full structured configuration
- All parameters included
- Easy parsing for applications

### WireGuard Format (`format=wg` or `/config/wg`)

- Standard WireGuard .conf file format
- Directly usable by WireGuard clients
- Human-readable

### Mobile Format (`format=mobile`)

- Optimized for mobile apps
- Separate arrays for multi-value fields
- Simplified structure

## Rate Limiting

- **Device endpoints**: 60 requests per minute per API key
- **IP-based limiting**: 10 requests per minute per source IP
- **Admin endpoints**: Subject to master session rate limits

## Security Headers

All responses include security headers:

```http
Cache-Control: no-store, no-cache, must-revalidate, private
Pragma: no-cache
Expires: 0
X-Content-Type-Options: nosniff
```

## Error Response Format

All error responses follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

## Common Error Messages

| Error                              | Description                          | Solution                     |
| ---------------------------------- | ------------------------------------ | ---------------------------- |
| "Invalid API key"                  | API key is missing or incorrect      | Check API key header         |
| "IP address not allowed"           | Source IP not in device's allowlist  | Add IP to device allowlist   |
| "Device not found"                 | Device ID does not exist             | Verify device ID             |
| "Device disabled"                  | Device has been revoked              | Contact administrator        |
| "Master password must be unlocked" | Admin access without master password | Unlock master password first |
| "Rate limit exceeded"              | Too many requests                    | Wait and retry               |

## Integration Examples

### Python Integration

```python
import requests

def get_device_config(device_id, api_key, base_url):
    """Get device configuration in JSON format."""
    url = f"{base_url}/api/devices/{device_id}/config"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def download_wg_config(device_id, api_key, base_url, filename):
    """Download WireGuard .conf file."""
    url = f"{base_url}/api/devices/{device_id}/config/wg"
    headers = {"Authorization": f"Bearer {api_key}"}

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    with open(filename, 'w') as f:
        f.write(response.text)
```

### Shell Script Integration

```bash
#!/bin/bash

# Configuration
DEVICE_ID="123e4567-e89b-12d3-a456-426614174000"
API_KEY="wg-device-api-key-12345" # pragma: allowlist secret
BASE_URL="https://<your-domain>"
CONFIG_FILE="/etc/wireguard/wg0.conf"

# Get device configuration
curl -X GET \
  "${BASE_URL}/api/devices/${DEVICE_ID}/config/wg" \
  -H "Authorization: Bearer ${API_KEY}" \
  -o "${CONFIG_FILE}"

# Set proper permissions
chmod 600 "${CONFIG_FILE}"
echo "Configuration saved to ${CONFIG_FILE}"
```

### Go Integration

```go
package main

import (
    "encoding/json"
    "fmt"
    "io"
    "net/http"
)

type DeviceConfig struct {
    DeviceID    string      `json:"device_id"`
    DeviceName  string      `json:"device_name"`
    NetworkName string      `json:"network_name"`
    Configuration interface{} `json:"configuration"`
    Format      string      `json:"format"`
    CreatedAt   string      `json:"created_at"`
}

func getDeviceConfig(baseURL, deviceID, apiKey string) (*DeviceConfig, error) {
    url := fmt.Sprintf("%s/api/devices/%s/config?format=json", baseURL, deviceID)

    req, err := http.NewRequest("GET", url, nil)
    if err != nil {
        return nil, err
    }

    req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", apiKey))
    req.Header.Set("Content-Type", "application/json")

    client := &http.Client{}
    resp, err := client.Do(req)
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()

    if resp.StatusCode != http.StatusOK {
        return nil, fmt.Errorf("API returned status: %d", resp.StatusCode)
    }

    var config DeviceConfig
    err = json.NewDecoder(resp.Body).Decode(&config)
    if err != nil {
        return nil, err
    }

    return &config, nil
}
```

## Testing the API

### Testing with curl

```bash
# Test JSON format
curl -v -X GET \
  "http://localhost:8000/api/devices/{device_id}/config?format=json" \
  -H "Authorization: Bearer your-api-key"

# Test WireGuard format
curl -v -X GET \
  "http://localhost:8000/api/devices/{device_id}/config/wg" \
  -H "Authorization: Bearer your-api-key"

# Test with mobile platform
curl -v -X GET \
  "http://localhost:8000/api/devices/{device_id}/config?format=mobile&platform=ios" \
  -H "Authorization: Bearer your-api-key"
```

## Configuration Validation

The API validates all configurations before returning them:

1. **Network CIDR validation**: Ensures IP addresses are within network CIDR
2. **Endpoint validation**: Validates host:port format
3. **Key validation**: Ensures public/private keys are valid WireGuard keys
4. **Device status**: Only enabled devices can retrieve configs

## Audit Logging

All configuration retrieval attempts are logged:

- **Successful retrievals**: Logged with device info, format, and source IP
- **Failed attempts**: Logged with error details and authentication info
- **Admin access**: Logged with master session information

Audit logs do not contain sensitive information like private keys or API keys.

## Troubleshooting

### Common Issues

1. **401 Unauthorized**

   - Check API key is correct
   - Ensure key hasn't been revoked
   - Verify key is being sent in the `Authorization: Bearer` header

2. **403 Forbidden**

   - Check source IP is in device's allowlist
   - If behind proxy, ensure `X-Forwarded-For` is set correctly

3. **404 Not Found**

   - Verify device ID is correct
   - Check device is enabled
   - Ensure device exists in the system

4. **423 Locked (Admin only)**
   - Master password must be unlocked first
   - Call the master password unlock endpoint

### Debug Tips

- Use verbose curl (`-v`) to see full HTTP request/response
- Check audit logs for detailed error information
- Verify network connectivity to the API endpoint
- Ensure proper timezone handling for timestamps
