# Device Config Fetcher (Device-Side Script)

This script runs on WireGuard devices to safely retrieve their own configuration
from the WireGuard Mesh Manager (WMM) API, test it, and roll back if needed.

## Requirements

- Python 3.11+
- `wg`, `wg-quick`, and `ping` available in `PATH`
- Root privileges (to apply WireGuard config)
- Device API key stored in a file or environment variable

## Script Location

- `scripts/device-config-fetcher.py`

## How It Works

1. Fetches the device config from WMM using the device API key.
2. Compares it with the local config file.
3. If unchanged, exits without changes.
4. If changed, applies the config and pings a peer through the WireGuard interface.
5. On success, keeps the new config; on failure, restores the previous config.

## Usage

```bash
sudo python3 scripts/device-config-fetcher.py \
  --base-url https://wg.example.com \
  --device-id 123e4567-e89b-12d3-a456-426614174000 \
  --api-key-file /etc/wireguard/device-api-key \
  --config-path /etc/wireguard/wg0.conf \
  --ping-target 10.0.0.3
```

## Cron Example (Linux)

Use root's crontab to run the fetcher periodically. Store the API key in a file
and ensure the script path is absolute.

```bash
sudo crontab -e
```

Example entry (every 5 minutes):

```cron
*/5 * * * * /usr/bin/python3 /zfs/wireguard/scripts/device-config-fetcher.py --base-url https://wg.example.com --device-id 123e4567-e89b-12d3-a456-426614174000 --api-key-file /etc/wireguard/device-api-key --config-path /etc/wireguard/wg0.conf --ping-target 10.0.0.3 >> /var/log/wmm-config-fetcher.log 2>&1
```

Optional dry-run (daily at 02:00):

```cron
0 2 * * * /usr/bin/python3 /zfs/wireguard/scripts/device-config-fetcher.py --dry-run --base-url https://wg.example.com --device-id 123e4567-e89b-12d3-a456-426614174000 --api-key-file /etc/wireguard/device-api-key --config-path /etc/wireguard/wg0.conf --ping-target 10.0.0.3 >> /var/log/wmm-config-fetcher.log 2>&1
```

### API Key Options

- File (preferred): `--api-key-file /path/to/key`
- Environment variable (default `WCM_DEVICE_API_KEY`):

```bash
export WCM_DEVICE_API_KEY="wg-device-api-key-12345"
sudo -E python3 scripts/device-config-fetcher.py \
  --base-url https://wg.example.com \
  --device-id 123e4567-e89b-12d3-a456-426614174000 \
  --ping-target 10.0.0.3
```

## Notes

- The script automatically appends `/api` to `--base-url` if missing.
- The config file is written with `0600` permissions.
- A backup is stored next to the config as `wg0.conf.wmm.bak`.
- If the interface is already up, the script uses `wg syncconf` to avoid
  unnecessary teardown; otherwise it uses `wg-quick up/down`.

## Exit Codes

- `0`: No change or successful apply
- `1`: Fetch/apply failed or ping test failed
