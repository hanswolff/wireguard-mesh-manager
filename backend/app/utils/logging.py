"""Structured logging configuration with redaction helpers."""

from __future__ import annotations

import logging
import sys
from typing import Any

from pythonjsonlogger import jsonlogger

REDACTED_PLACEHOLDER = "[REDACTED]"


class RedactingJsonFormatter(jsonlogger.JsonFormatter):
    """JSON formatter that redacts sensitive information."""

    SENSITIVE_PATTERNS = {
        "private",
        "private_key",
        "private_key_encrypted",
        "device_dek_encrypted_master",
        "device_dek_encrypted_api_key",
        "device_dek_encrypted",
        "public_key",
        "preshared_key",
        "preshared_key_encrypted",
        "network_preshared_key_encrypted",
        "location_preshared_key_encrypted",
        "secret",
        "key_hash",
        "key_fingerprint",
        "api_key",
        "authorization",
        "auth",
        "bearer",
        "credential",
        "master_password",
        "_password",
    }

    # Patterns that are safe in logger names (module paths) but not in values
    LOGGER_NAME_SAFE_PATTERNS = {
        "master_password",
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the redacting JSON formatter."""
        super().__init__(*args, **kwargs)

    def process_log_record(self, log_record: dict[str, Any]) -> dict[str, Any]:
        """Process log record and redact sensitive information."""
        # Don't redact the logger name (it's just a module path)
        # Redact sensitive fields but not the logger name itself
        sensitive_keys_to_redact = set(log_record.keys()) - {
            "name",
            "levelname",
            "asctime",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "filename",
            "module",
            "lineno",
            "funcName",
            "pathname",
            "message",
            "service_name",
            "request_id",
            "correlation_id",
        }
        for key in sensitive_keys_to_redact:
            if self._is_sensitive_key(key, is_logger_name=False):
                log_record[key] = REDACTED_PLACEHOLDER
            elif isinstance(log_record[key], dict):
                self._redact_sensitive_data(log_record[key])
            elif isinstance(log_record[key], list):
                log_record[key] = self._redact_value(key, log_record[key])

        return super().process_log_record(log_record)

    def _redact_sensitive_data(self, data: dict[str, Any]) -> None:
        """Recursively redact sensitive data from dictionary."""
        for key, value in list(data.items()):
            data[key] = self._redact_value(key, value)

    def _redact_value(self, key: str, value: Any) -> Any:
        """Redact a value based on its key and content."""
        if self._is_sensitive_key(key, is_logger_name=False):
            return REDACTED_PLACEHOLDER

        if isinstance(value, dict):
            self._redact_sensitive_data(value)
            return value

        if isinstance(value, list):
            redacted_list: list[Any] = []
            for item in value:
                if isinstance(item, dict):
                    redacted_item = item.copy()
                    self._redact_sensitive_data(redacted_item)
                    redacted_list.append(redacted_item)
                elif self._contains_sensitive_content(str(item)):
                    redacted_list.append(REDACTED_PLACEHOLDER)
                else:
                    redacted_list.append(item)
            return redacted_list

        if isinstance(value, str) and self._contains_sensitive_content(value):
            return REDACTED_PLACEHOLDER

        return value

    def _is_sensitive_key(self, key: str, is_logger_name: bool = False) -> bool:
        """Check if a key contains sensitive patterns.

        Args:
            key: The key to check
            is_logger_name: Whether this is a logger name (module path) which has safe patterns
        """
        key_lower = key.lower()
        for pattern in self.SENSITIVE_PATTERNS:
            if pattern in key_lower:
                # Skip if this is a logger name and pattern is safe for logger names
                if is_logger_name and pattern in self.LOGGER_NAME_SAFE_PATTERNS:
                    continue
                return True
        return False

    def _contains_sensitive_content(self, content: str) -> bool:
        """Check if content contains sensitive patterns."""
        return any(pattern in content.lower() for pattern in self.SENSITIVE_PATTERNS)

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON."""
        # Add service context
        record.service_name = getattr(
            record, "service_name", "wireguard-mesh-manager"
        )
        record.request_id = getattr(record, "request_id", None)
        record.correlation_id = getattr(record, "correlation_id", None)

        return super().format(record)


def setup_logging(
    level: str = "INFO", service_name: str = "wireguard-mesh-manager"
) -> None:
    """Setup structured logging with JSON formatting and redaction."""

    # Remove existing handlers to avoid duplicate logs
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create redacting JSON formatter
    formatter = RedactingJsonFormatter("%(asctime)s %(name)s %(levelname)s %(message)s")

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    # Configure root logger
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)

    # Configure specific loggers
    logging.getLogger("uvicorn").setLevel(level)
    logging.getLogger("uvicorn.access").setLevel(level)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.WARNING if level == "INFO" else level
    )

    # Prevent propagation to avoid duplicate logs
    logging.getLogger("uvicorn").propagate = False
    logging.getLogger("uvicorn.access").propagate = False


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(name)
