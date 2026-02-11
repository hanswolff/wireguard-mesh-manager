"""Application configuration settings."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = "WireGuard Mesh Manager API"
    app_version: str = "1.0.0"
    debug: bool = False
    service_name: str = "wireguard-mesh-manager"
    host: str = "0.0.0.0"
    port: int = 8000
    database_url: str = "sqlite+aiosqlite:///./data/wireguard.db"

    # Logging settings
    log_level: str = "INFO"
    log_format: str = "json"  # "json" or "text"

    # Request hardening settings
    max_request_size: int = 1024 * 1024  # 1MB max request size
    request_timeout: int = 30  # 30 seconds timeout
    max_json_depth: int = 100  # Maximum JSON nesting depth
    max_string_length: int = 10_000  # Maximum string field length
    max_items_per_array: int = 1000  # Maximum items in array fields

    # Audit settings
    audit_retention_days: int = 365  # Default retention period of 1 year
    audit_export_batch_size: int = (
        10_000  # Number of events to export in a single batch
    )

    # Master password cache settings
    master_password_ttl_hours: float = 1.0  # TTL for master password cache in hours
    master_password_idle_timeout_minutes: float = (
        30.0  # Idle timeout for master password cache in minutes
    )
    master_password_per_user_session: bool = (
        False  # Whether to use per-user session cache instead of global cache
    )

    # Trusted proxy settings for X-Forwarded-For handling
    # Comma-separated list of trusted proxy IP addresses or CIDR ranges
    # Examples: "192.168.1.100,10.0.0.0/8,172.16.0.0/12"
    trusted_proxies: str = ""  # Empty means no trusted proxies (deny-by-default)

    # CORS settings
    # Comma-separated list of allowed origins for cross-origin requests
    # Examples: "http://localhost:3000,https://admin.example.com"
    cors_origins: str = (
        "http://localhost:3000,http://127.0.0.1:3000"  # Default to localhost dev
    )
    cors_allow_credentials: bool = True  # Allow credentials in CORS requests
    cors_allow_methods: list[str] = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
    cors_allow_headers: list[str] = [
        "authorization",
        "content-type",
        "accept",
        "origin",
        "x-requested-with",
        "x-api-key",
        "x-csrf-token",
    ]

    # Rate limit settings
    rate_limit_backend: str = "redis"  # "redis" or "memory"
    rate_limit_redis_url: str = "redis://redis:6379/0"
    rate_limit_redis_prefix: str = "wmm:ratelimit"
    rate_limit_api_key_window: int = 60
    rate_limit_api_key_max_requests: int = 60
    rate_limit_ip_window: int = 60
    rate_limit_ip_max_requests: int = 10

    # CSRF settings
    # Enable CSRF protection for admin browser flows
    csrf_protection_enabled: bool = True
    # CSRF token expiration time in seconds (default: 1 hour)
    csrf_token_ttl_seconds: int = 3600

    # Bootstrap settings
    # Token required for initial master-password unlock when database is empty
    # Required to prevent unauthenticated bootstrap on fresh installs
    # Once bootstrapped (has encrypted data), this token is no longer required
    bootstrap_token: str = ""  # Empty disables bootstrap protection (INSECURE for production)

    # Registration settings
    allow_registration: bool = False  # Disable self-service registration in production


settings = Settings()
