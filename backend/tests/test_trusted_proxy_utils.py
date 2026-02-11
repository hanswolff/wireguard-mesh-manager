"""Unit tests for trusted proxy utility functions."""

from __future__ import annotations

from fastapi import Request

from app.routers.utils import (
    _get_source_ip,
    _is_trusted_proxy,
    _parse_trusted_proxies,
)


class TestTrustedProxyUtils:
    """Test trusted proxy utility functions."""

    def test_parse_trusted_proxies_empty(self) -> None:
        """Test parsing empty trusted proxy configuration."""
        from app.config import settings

        original_trusted_proxies = settings.trusted_proxies

        try:
            settings.trusted_proxies = ""
            trusted_networks = _parse_trusted_proxies()
            assert trusted_networks == ()
        finally:
            settings.trusted_proxies = original_trusted_proxies
            _parse_trusted_proxies.cache_clear()

    def test_parse_trusted_proxies_single_ip(self) -> None:
        """Test parsing single IP in trusted proxy configuration."""
        import ipaddress

        from app.config import settings

        original_trusted_proxies = settings.trusted_proxies

        try:
            settings.trusted_proxies = "192.168.1.100"
            trusted_networks = _parse_trusted_proxies()
            assert len(trusted_networks) == 1
            assert isinstance(trusted_networks[0], ipaddress.IPv4Network)
            assert str(trusted_networks[0]) == "192.168.1.100/32"
        finally:
            settings.trusted_proxies = original_trusted_proxies
            _parse_trusted_proxies.cache_clear()

    def test_parse_trusted_proxies_cidr(self) -> None:
        """Test parsing CIDR network in trusted proxy configuration."""
        import ipaddress

        from app.config import settings

        original_trusted_proxies = settings.trusted_proxies

        try:
            settings.trusted_proxies = "10.0.0.0/8"
            trusted_networks = _parse_trusted_proxies()
            assert len(trusted_networks) == 1
            assert isinstance(trusted_networks[0], ipaddress.IPv4Network)
            assert str(trusted_networks[0]) == "10.0.0.0/8"
        finally:
            settings.trusted_proxies = original_trusted_proxies
            _parse_trusted_proxies.cache_clear()

    def test_parse_trusted_proxies_multiple_entries(self) -> None:
        """Test parsing multiple entries in trusted proxy configuration."""

        from app.config import settings

        original_trusted_proxies = settings.trusted_proxies

        try:
            settings.trusted_proxies = "192.168.1.100,10.0.0.0/8,172.16.0.0/12"
            trusted_networks = _parse_trusted_proxies()
            assert len(trusted_networks) == 3
            assert str(trusted_networks[0]) == "192.168.1.100/32"
            assert str(trusted_networks[1]) == "10.0.0.0/8"
            assert str(trusted_networks[2]) == "172.16.0.0/12"
        finally:
            settings.trusted_proxies = original_trusted_proxies
            _parse_trusted_proxies.cache_clear()

    def test_parse_trusted_proxies_with_whitespace(self) -> None:
        """Test parsing trusted proxy configuration with whitespace."""

        from app.config import settings

        original_trusted_proxies = settings.trusted_proxies

        try:
            settings.trusted_proxies = " 192.168.1.100 , 10.0.0.0/8 , "
            trusted_networks = _parse_trusted_proxies()
            assert len(trusted_networks) == 2
            assert str(trusted_networks[0]) == "192.168.1.100/32"
            assert str(trusted_networks[1]) == "10.0.0.0/8"
        finally:
            settings.trusted_proxies = original_trusted_proxies
            _parse_trusted_proxies.cache_clear()

    def test_parse_trusted_proxies_invalid_entries(self) -> None:
        """Test parsing trusted proxy configuration with invalid entries."""
        from app.config import settings

        original_trusted_proxies = settings.trusted_proxies

        try:
            settings.trusted_proxies = "192.168.1.100,invalid_ip,10.0.0.0/8"
            trusted_networks = _parse_trusted_proxies()
            # Should skip invalid entries and parse valid ones
            assert len(trusted_networks) == 2
        finally:
            settings.trusted_proxies = original_trusted_proxies
            _parse_trusted_proxies.cache_clear()

    def test_is_trusted_proxy_empty_config(self) -> None:
        """Test trusted proxy check with empty configuration."""
        from app.config import settings

        original_trusted_proxies = settings.trusted_proxies

        try:
            settings.trusted_proxies = ""
            assert not _is_trusted_proxy("192.168.1.100")
        finally:
            settings.trusted_proxies = original_trusted_proxies
            _parse_trusted_proxies.cache_clear()

    def test_is_trusted_proxy_matching_ip(self) -> None:
        """Test trusted proxy check with matching IP."""
        from app.config import settings

        original_trusted_proxies = settings.trusted_proxies

        try:
            settings.trusted_proxies = "192.168.1.100"
            assert _is_trusted_proxy("192.168.1.100")
        finally:
            settings.trusted_proxies = original_trusted_proxies
            _parse_trusted_proxies.cache_clear()

    def test_is_trusted_proxy_matching_cidr(self) -> None:
        """Test trusted proxy check with matching CIDR."""
        from app.config import settings

        original_trusted_proxies = settings.trusted_proxies

        try:
            settings.trusted_proxies = "10.0.0.0/8"
            assert _is_trusted_proxy("10.1.2.3")
            assert not _is_trusted_proxy("192.168.1.100")
        finally:
            settings.trusted_proxies = original_trusted_proxies
            _parse_trusted_proxies.cache_clear()

    def test_is_trusted_proxy_invalid_ip(self) -> None:
        """Test trusted proxy check with invalid IP."""
        from app.config import settings

        original_trusted_proxies = settings.trusted_proxies

        try:
            settings.trusted_proxies = "192.168.1.100"
            assert not _is_trusted_proxy("invalid_ip")
        finally:
            settings.trusted_proxies = original_trusted_proxies
            _parse_trusted_proxies.cache_clear()

    def test_get_source_ip_without_forwarded_header(self) -> None:
        """Test source IP extraction without X-Forwarded-For header."""
        # Create a mock request
        request = Request(
            {
                "type": "http",
                "client": ("192.168.1.100", 12345),
                "headers": {},
            }
        )

        source_ip = _get_source_ip(request)
        assert source_ip == "192.168.1.100"

    def test_get_source_ip_with_forwarded_header_no_trust(self) -> None:
        """Test source IP extraction with X-Forwarded-For from untrusted proxy."""
        from app.config import settings

        original_trusted_proxies = settings.trusted_proxies

        try:
            settings.trusted_proxies = ""  # No trusted proxies

            request = Request(
                {
                    "type": "http",
                    "client": ("192.168.1.100", 12345),
                    "headers": [(b"x-forwarded-for", b"203.0.113.1")],
                }
            )

            # Should ignore X-Forwarded-For and use client IP
            source_ip = _get_source_ip(request)
            assert source_ip == "192.168.1.100"

        finally:
            settings.trusted_proxies = original_trusted_proxies
            _parse_trusted_proxies.cache_clear()

    def test_get_source_ip_with_forwarded_header_with_trust(self) -> None:
        """Test source IP extraction with X-Forwarded-For from trusted proxy."""
        from app.config import settings

        original_trusted_proxies = settings.trusted_proxies

        try:
            settings.trusted_proxies = "192.168.1.100"  # Trust the client IP

            request = Request(
                {
                    "type": "http",
                    "client": ("192.168.1.100", 12345),
                    "headers": [(b"x-forwarded-for", b"203.0.113.1")],
                }
            )

            # Should use X-Forwarded-For since client is trusted
            source_ip = _get_source_ip(request)
            assert source_ip == "203.0.113.1"

        finally:
            settings.trusted_proxies = original_trusted_proxies
            _parse_trusted_proxies.cache_clear()

    def test_get_source_ip_with_multiple_forwarded_ips(self) -> None:
        """Test source IP extraction with multiple IPs in X-Forwarded-For."""
        from app.config import settings

        original_trusted_proxies = settings.trusted_proxies

        try:
            settings.trusted_proxies = "192.168.1.100"  # Trust the client IP

            request = Request(
                {
                    "type": "http",
                    "client": ("192.168.1.100", 12345),
                    "headers": [
                        (b"x-forwarded-for", b"203.0.113.1, 10.0.0.1, 172.16.0.1")
                    ],
                }
            )

            # Should use the first IP (original client)
            source_ip = _get_source_ip(request)
            assert source_ip == "203.0.113.1"

        finally:
            settings.trusted_proxies = original_trusted_proxies
            _parse_trusted_proxies.cache_clear()

    def test_get_source_ip_no_client_info(self) -> None:
        """Test source IP extraction when no client info is available."""
        request = Request(
            {
                "type": "http",
                "headers": [],
            }
        )

        source_ip = _get_source_ip(request)
        assert source_ip == "unknown"
