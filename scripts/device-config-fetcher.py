#!/usr/bin/env python3
"""Fetch and safely apply WireGuard configs from the WMM API."""

from __future__ import annotations

import argparse
import ipaddress
import os
import shutil
import ssl
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path


DEFAULT_API_KEY_ENV = "WCM_DEVICE_API_KEY"


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Fetch a device WireGuard config from WMM and apply it with rollback."
        )
    )
    parser.add_argument(
        "--base-url",
        required=True,
        help="WMM base URL (e.g. https://wg.example.com or https://wg.example.com/api)",
    )
    parser.add_argument("--device-id", required=True, help="Device UUID")
    parser.add_argument(
        "--api-key-file",
        type=Path,
        help="Path to the API key file (preferred over env)",
    )
    parser.add_argument(
        "--api-key-env",
        default=DEFAULT_API_KEY_ENV,
        help=f"Environment variable holding API key (default: {DEFAULT_API_KEY_ENV})",
    )
    parser.add_argument(
        "--config-path",
        type=Path,
        default=Path("/etc/wireguard/wg0.conf"),
        help="Path to WireGuard config file (default: /etc/wireguard/wg0.conf)",
    )
    parser.add_argument(
        "--interface",
        help="WireGuard interface name (default: derived from config filename)",
    )
    parser.add_argument(
        "--ping-target",
        required=True,
        help="WireGuard peer IP to ping after applying config",
    )
    parser.add_argument(
        "--ping-count",
        type=int,
        default=3,
        help="Ping packet count (default: 3)",
    )
    parser.add_argument(
        "--ping-timeout",
        type=int,
        default=2,
        help="Ping timeout seconds per packet (default: 2)",
    )
    parser.add_argument(
        "--request-timeout",
        type=int,
        default=10,
        help="HTTP request timeout seconds (default: 10)",
    )
    parser.add_argument(
        "--ca-bundle",
        type=Path,
        help="Custom CA bundle for TLS verification",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without applying configuration",
    )
    return parser.parse_args()


def require_command(name: str) -> str:
    """Ensure a required command exists in PATH."""
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"Required command '{name}' not found in PATH.")
    return path


def normalize_base_url(base_url: str) -> str:
    """Normalize the base URL to include the /api prefix."""
    normalized = base_url.rstrip("/")
    if not normalized.endswith("/api"):
        normalized = f"{normalized}/api"
    return normalized


def read_api_key(api_key_file: Path | None, api_key_env: str) -> str:
    """Load the API key from file or environment."""
    if api_key_file:
        key = api_key_file.read_text(encoding="utf-8").strip()
    else:
        key = os.environ.get(api_key_env, "").strip()
    if not key:
        source = str(api_key_file) if api_key_file else api_key_env
        raise RuntimeError(f"API key not found in {source}.")
    return key


def canonicalize_config(config_text: str) -> str:
    """Normalize config text for stable comparisons."""
    lines = [line.rstrip() for line in config_text.splitlines()]
    normalized = "\n".join(lines).strip()
    if not normalized:
        return ""
    return f"{normalized}\n"


def fetch_config(
    base_url: str,
    device_id: str,
    api_key: str,
    timeout: int,
    ca_bundle: Path | None,
) -> str:
    """Fetch WireGuard config from the WMM API."""
    url = f"{base_url}/devices/{device_id}/config/wg"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "text/plain",
    }
    request = urllib.request.Request(url, headers=headers, method="GET")
    context = ssl.create_default_context()
    if ca_bundle:
        context.load_verify_locations(cafile=str(ca_bundle))
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=context) as resp:
            payload = resp.read()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"Config fetch failed with status {exc.code}."
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Config fetch failed: {exc.reason}.") from exc

    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError("Config fetch returned non-UTF-8 data.") from exc


def write_secure_file(path: Path, content: str) -> None:
    """Write content to a file with strict permissions."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    os.chmod(path, 0o600)


def interface_exists(interface: str) -> bool:
    """Check whether the WireGuard interface exists."""
    require_command("wg")
    result = subprocess.run(
        ["wg", "show", interface],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def get_runtime_config(interface: str) -> str:
    """Fetch the currently applied WireGuard config for rollback."""
    require_command("wg")
    result = subprocess.run(
        ["wg", "showconf", interface],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def setconf(interface: str, config_path: Path) -> None:
    """Apply a wg setconf-compatible config file."""
    require_command("wg")
    subprocess.run(
        ["wg", "setconf", interface, str(config_path)],
        check=True,
    )


def syncconf(interface: str, config_path: Path) -> None:
    """Apply config using wg syncconf."""
    require_command("wg")
    require_command("wg-quick")
    strip_result = subprocess.run(
        ["wg-quick", "strip", str(config_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
        temp_file.write(strip_result.stdout)
        temp_path = Path(temp_file.name)
    try:
        subprocess.run(
            ["wg", "syncconf", interface, str(temp_path)],
            check=True,
        )
    finally:
        temp_path.unlink(missing_ok=True)


def wg_quick_up(config_path: Path) -> None:
    """Bring up an interface with wg-quick."""
    require_command("wg-quick")
    subprocess.run(["wg-quick", "up", str(config_path)], check=True)


def wg_quick_down(config_path: Path) -> None:
    """Bring down an interface with wg-quick."""
    require_command("wg-quick")
    subprocess.run(["wg-quick", "down", str(config_path)], check=True)


def ping_peer(
    interface: str,
    target: str,
    count: int,
    timeout: int,
) -> bool:
    """Ping a peer through the WireGuard interface."""
    target_ip = ipaddress.ip_address(target)
    if target_ip.version == 6:
        ping_cmd = shutil.which("ping6") or "ping"
        cmd = [ping_cmd, "-6"]
    else:
        cmd = ["ping"]
    cmd.extend(["-c", str(count), "-W", str(timeout), "-I", interface, target])
    result = subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def main() -> int:
    """Run the config fetch/apply workflow."""
    args = parse_args()
    if os.geteuid() != 0:
        raise RuntimeError("This script must be run as root.")

    api_key = read_api_key(args.api_key_file, args.api_key_env)
    base_url = normalize_base_url(args.base_url)
    config_path = args.config_path
    interface = args.interface or config_path.stem

    new_config_raw = fetch_config(
        base_url=base_url,
        device_id=args.device_id,
        api_key=api_key,
        timeout=args.request_timeout,
        ca_bundle=args.ca_bundle,
    )
    new_config = canonicalize_config(new_config_raw)

    current_config = None
    if config_path.exists():
        current_config = config_path.read_text(encoding="utf-8")
        current_normalized = canonicalize_config(current_config)
        if current_normalized == new_config:
            print("Config unchanged; no action taken.")
            return 0
        if args.dry_run:
            print("Config differs; dry-run mode, no changes applied.")
            return 0
    elif args.dry_run:
        print("Config missing; dry-run mode, no changes applied.")
        return 0

    backup_path = config_path.with_suffix(f"{config_path.suffix}.wmm.bak")
    runtime_backup_path: Path | None = None
    interface_up = interface_exists(interface)
    if current_config is not None:
        write_secure_file(backup_path, current_config)
    elif interface_up:
        with tempfile.NamedTemporaryFile(
            mode="w",
            prefix=f"{interface}.wmm.runtime.",
            suffix=".conf",
            delete=False,
        ) as runtime_file:
            runtime_file.write(get_runtime_config(interface))
            runtime_backup_path = Path(runtime_file.name)
        os.chmod(runtime_backup_path, 0o600)

    with tempfile.NamedTemporaryFile(
        mode="w",
        prefix=f"{config_path.stem}.wmm.staging.",
        suffix=config_path.suffix,
        dir=str(config_path.parent),
        delete=False,
    ) as staging_file:
        staging_file.write(new_config)
        staging_path = Path(staging_file.name)
    os.chmod(staging_path, 0o600)

    try:
        if interface_up:
            print("Applying candidate config via wg syncconf.")
            syncconf(interface, staging_path)
            if ping_peer(
                interface,
                args.ping_target,
                args.ping_count,
                args.ping_timeout,
            ):
                write_secure_file(config_path, new_config)
                print("Config applied and validated.")
                return 0

            print("Ping failed; reverting to previous config.")
            if current_config is not None:
                syncconf(interface, backup_path)
                write_secure_file(config_path, current_config)
            elif runtime_backup_path is not None:
                setconf(interface, runtime_backup_path)
            return 1

        print("Interface is down; applying candidate config via wg-quick.")
        write_secure_file(config_path, new_config)
        wg_quick_up(config_path)
        if ping_peer(
            interface,
            args.ping_target,
            args.ping_count,
            args.ping_timeout,
        ):
            print("Config applied and validated.")
            return 0

        print("Ping failed; rolling back.")
        wg_quick_down(config_path)
        if current_config is not None:
            write_secure_file(config_path, current_config)
        else:
            config_path.unlink(missing_ok=True)
        return 1
    finally:
        staging_path.unlink(missing_ok=True)
        if runtime_backup_path is not None:
            runtime_backup_path.unlink(missing_ok=True)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
