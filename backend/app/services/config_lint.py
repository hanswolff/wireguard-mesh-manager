"""Service for linting WireGuard network configurations."""

from __future__ import annotations

import ipaddress
from typing import Any

from app.schemas.config_lint import (
    Category,
    ConfigLintRequest,
    ConfigLintResponse,
    DeviceLint,
    LintIssue,
    LocationLint,
    Severity,
)
from app.utils.validation import (
    ValidationError,
    validate_dns_servers,
    validate_external_endpoint,
    validate_host,
    validate_mtu,
    validate_network_cidr,
    validate_persistent_keepalive,
    validate_wireguard_public_key,
)


class ConfigLintService:
    """Service for validating WireGuard network configurations."""

    def __init__(self) -> None:
        self.issues: list[LintIssue] = []

    def lint_config(self, config: ConfigLintRequest) -> ConfigLintResponse:
        """Lint a WireGuard network configuration."""
        self.issues = []

        self._validate_network(config)
        self._validate_locations(config.locations)
        self._validate_devices(config.devices, config.network_cidr)
        self._validate_relationships(config)

        issue_count = self._count_issues()
        summary = self._generate_summary(issue_count)

        return ConfigLintResponse(
            valid=issue_count["error"] == 0,
            issue_count=issue_count,
            issues=self.issues,
            summary=summary,
        )

    def _add_issue(
        self,
        severity: Severity,
        category: Category,
        field: str,
        message: str,
        suggestion: str | None = None,
    ) -> None:
        """Add a validation issue to the issues list."""
        self.issues.append(
            LintIssue(
                severity=severity,
                category=category,
                field=field,
                message=message,
                suggestion=suggestion,
            )
        )

    def _validate_with_suggestion(
        self,
        validator: Any,
        value: Any,
        severity: Severity,
        category: Category,
        field: str,
        field_display: str,
        suggestion: str,
    ) -> None:
        """Validate a field and add an issue with a custom suggestion if validation fails."""
        try:
            validator(value)
        except ValidationError as e:
            self._add_issue(
                severity=severity,
                category=category,
                field=field,
                message=str(e),
                suggestion=suggestion,
            )

    def _validate_network(self, config: ConfigLintRequest) -> None:
        """Validate network-level configuration."""
        self._validate_with_suggestion(
            validate_network_cidr,
            config.network_cidr,
            Severity.ERROR,
            Category.NETWORK,
            "network_cidr",
            "Network CIDR",
            "Use a valid IPv4 CIDR (e.g., 10.0.0.0/24) with prefix length 8-32",
        )

        if config.dns_servers:
            self._validate_with_suggestion(
                validate_dns_servers,
                config.dns_servers,
                Severity.ERROR,
                Category.NETWORK,
                "dns_servers",
                "DNS servers",
                "Use comma-separated IP addresses or domain names (e.g., 8.8.8.8,1.1.1.1)",
            )

        if config.mtu is not None:
            self._validate_with_suggestion(
                validate_mtu,
                config.mtu,
                Severity.ERROR,
                Category.NETWORK,
                "mtu",
                "MTU",
                "Use an MTU between 576 and 9000 bytes (typical: 1420 for WireGuard)",
            )

        if config.persistent_keepalive is not None:
            self._validate_with_suggestion(
                validate_persistent_keepalive,
                config.persistent_keepalive,
                Severity.ERROR,
                Category.NETWORK,
                "persistent_keepalive",
                "Persistent keepalive",
                "Use a keepalive between 0 and 86400 seconds (typical: 25)",
            )

        if config.public_key:
            self._validate_with_suggestion(
                validate_wireguard_public_key,
                config.public_key,
                Severity.ERROR,
                Category.NETWORK,
                "public_key",
                "Public key",
                "Generate a new WireGuard key pair using 'wg genkey' and 'wg pubkey'",
            )

    def _validate_locations(self, locations: list[LocationLint]) -> None:
        """Validate location configurations."""
        location_names = set()

        for i, location in enumerate(locations):
            if location.name in location_names:
                self._add_issue(
                    Severity.ERROR,
                    Category.LOCATION,
                    "name",
                    f"Duplicate location name: {location.name}",
                    f"Rename location at index {i} to have a unique name",
                )
            location_names.add(location.name)

            if location.external_endpoint:
                try:
                    # Location external_endpoint should be a hostname or IP without port
                    # Devices have external_endpoint with ports, locations do not
                    validate_host(location.external_endpoint)
                except ValidationError as e:
                    self._add_issue(
                        Severity.WARNING,
                        Category.LOCATION,
                        "external_endpoint",
                        f"Invalid external endpoint for location '{location.name}': {str(e)}",
                        "Use a hostname or IP address without port (e.g., 'vpn.example.com' or '1.2.3.4')",
                    )

    def _validate_devices(self, devices: list[DeviceLint], network_cidr: str) -> None:
        """Validate device configurations."""
        device_names: set[str] = set()
        device_ips: set[str] = set()
        public_keys: set[str] = set()

        try:
            network = ipaddress.IPv4Network(network_cidr, strict=True)
        except Exception:
            return

        for i, device in enumerate(devices):
            self._validate_device_name(device, i, device_names)
            self._validate_device_ip(device, network, device_ips)
            self._validate_device_keys(device, public_keys)

    def _validate_device_name(
        self, device: DeviceLint, index: int, device_names: set[str]
    ) -> None:
        """Validate device name uniqueness."""
        if device.name in device_names:
            self._add_issue(
                Severity.ERROR,
                Category.DEVICE,
                "name",
                f"Duplicate device name: {device.name}",
                f"Rename device at index {index} to have a unique name",
            )
        device_names.add(device.name)

    def _validate_device_ip(
        self, device: DeviceLint, network: ipaddress.IPv4Network, device_ips: set[str]
    ) -> None:
        """Validate device IP address."""
        if not device.wireguard_ip:
            return

        try:
            ip = ipaddress.IPv4Address(device.wireguard_ip)

            if ip not in network:
                self._add_issue(
                    Severity.ERROR,
                    Category.DEVICE,
                    "wireguard_ip",
                    f"Device '{device.name}' IP {device.wireguard_ip} is not in network {network}",
                    f"Use an IP within the network range, e.g., {network.network_address + 1}",
                )

            if device.wireguard_ip in device_ips:
                self._add_issue(
                    Severity.ERROR,
                    Category.DEVICE,
                    "wireguard_ip",
                    f"Duplicate IP address: {device.wireguard_ip}",
                    f"Assign a unique IP to device '{device.name}'",
                )
            device_ips.add(device.wireguard_ip)

            if ip == network.network_address:
                self._add_issue(
                    Severity.ERROR,
                    Category.DEVICE,
                    "wireguard_ip",
                    f"Device '{device.name}' cannot use network address: {device.wireguard_ip}",
                    f"Use {network.network_address + 1} or another available IP",
                )
            elif ip == network.broadcast_address:
                self._add_issue(
                    Severity.WARNING,
                    Category.DEVICE,
                    "wireguard_ip",
                    f"Device '{device.name}' is using broadcast address: {device.wireguard_ip}",
                    "Consider using a different IP within the network",
                )

        except ipaddress.AddressValueError:
            self._add_issue(
                Severity.ERROR,
                Category.DEVICE,
                "wireguard_ip",
                f"Invalid IPv4 address for device '{device.name}': {device.wireguard_ip}",
                "Use a valid IPv4 address format (e.g., 10.0.0.1)",
            )

    def _validate_device_keys(self, device: DeviceLint, public_keys: set[str]) -> None:
        """Validate device public and preshared keys."""
        if device.public_key:
            try:
                validate_wireguard_public_key(device.public_key)

                if device.public_key in public_keys:
                    self._add_issue(
                        Severity.ERROR,
                        Category.DEVICE,
                        "public_key",
                        f"Duplicate public key for device '{device.name}'",
                        "Generate a unique key pair for each device",
                    )
                public_keys.add(device.public_key)

            except ValidationError as e:
                self._add_issue(
                    Severity.ERROR,
                    Category.DEVICE,
                    "public_key",
                    f"Invalid public key for device '{device.name}': {str(e)}",
                    "Generate a new key pair using 'wg genkey' and 'wg pubkey'",
                )

        if device.preshared_key:
            try:
                validate_wireguard_public_key(device.preshared_key)
            except ValidationError:
                self._add_issue(
                    Severity.ERROR,
                    Category.DEVICE,
                    "preshared_key",
                    f"Invalid preshared key format for device '{device.name}'",
                    "Generate a preshared key using 'wg genpsk' or omit for no preshared key",
                )

    def _validate_relationships(self, config: ConfigLintRequest) -> None:
        """Validate cross-component relationships."""
        if config.devices and not config.locations:
            self._add_issue(
                Severity.WARNING,
                Category.GENERAL,
                "locations",
                "Devices defined but no locations configured",
                "Add at least one location for proper network topology",
            )

        if config.locations and not config.devices:
            self._add_issue(
                Severity.INFO,
                Category.GENERAL,
                "devices",
                "Locations configured but no devices defined",
                "Add devices to make use of the configured locations",
            )

        if not config.locations and not config.devices:
            self._add_issue(
                Severity.INFO,
                Category.GENERAL,
                "configuration",
                "Empty configuration - only network settings defined",
                "Add locations and devices to create a complete WireGuard network",
            )

        self._validate_network_capacity(config)

    def _validate_network_capacity(self, config: ConfigLintRequest) -> None:
        """Validate if network has enough IP addresses for all devices."""
        if not config.network_cidr:
            return

        try:
            network = ipaddress.IPv4Network(config.network_cidr, strict=True)
            usable_ips = list(network.hosts())

            reserved_ips = 2
            if config.public_key:
                reserved_ips += 1

            available_ips = len(usable_ips) - reserved_ips

            if available_ips < len(config.devices):
                self._add_issue(
                    Severity.ERROR,
                    Category.GENERAL,
                    "network_cidr",
                    f"Network {config.network_cidr} has only {available_ips} available IPs but {len(config.devices)} devices configured",
                    f"Use a larger network (e.g., /{max(8, network.prefixlen - 1)}) or reduce number of devices",
                )

        except Exception:
            pass

    def _count_issues(self) -> dict[str, int]:
        """Count issues by severity."""
        issue_count = {"error": 0, "warning": 0, "info": 0}
        for issue in self.issues:
            issue_count[issue.severity.value] = (
                issue_count.get(issue.severity.value, 0) + 1
            )
        return issue_count

    def _generate_summary(self, issue_count: dict[str, int]) -> str:
        """Generate a human-readable summary of lint results."""
        total_issues = sum(issue_count.values())

        if total_issues == 0:
            return "Configuration is valid with no issues found."

        summary_parts = []
        for severity, count in issue_count.items():
            if count > 0:
                summary_parts.append(f"{count} {severity}{'s' if count != 1 else ''}")

        if issue_count.get("error", 0) > 0:
            return f"Configuration has {', '.join(summary_parts)}. Fix errors before deployment."
        else:
            return f"Configuration is valid but has {', '.join(summary_parts)}. Consider addressing warnings."
