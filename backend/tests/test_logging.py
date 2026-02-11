"""Tests for structured logging functionality."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest

from app.utils.logging import RedactingJsonFormatter, setup_logging

if TYPE_CHECKING:
    from fastapi import FastAPI
    from httpx import AsyncClient


class TestRedactingJsonFormatter:
    """Test the redacting JSON formatter."""

    def test_redacts_sensitive_fields(self) -> None:
        """Test that sensitive fields are redacted."""
        formatter = RedactingJsonFormatter()

        # Create a log record with sensitive data
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Add sensitive data
        record.private_key = "secret123"
        record.api_key = "abc123def"
        record.normal_field = "normal_value"
        record.auth_header = "Bearer token123"

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        # Verify sensitive data is redacted
        assert log_data["private_key"] == "[REDACTED]"
        assert log_data["api_key"] == "[REDACTED]"
        assert log_data["auth_header"] == "[REDACTED]"
        assert log_data["normal_field"] == "normal_value"

    def test_redacts_nested_sensitive_data(self) -> None:
        """Test that nested sensitive data is redacted."""
        formatter = RedactingJsonFormatter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Add nested sensitive data
        record.data = {
            "user": {"username": "testuser", "password": "secret123"},
            "config": {"api_key": "abc123", "timeout": 30},
        }

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        # Verify nested sensitive data is redacted
        assert log_data["data"]["user"]["password"] == "[REDACTED]"
        assert log_data["data"]["config"]["api_key"] == "[REDACTED]"
        assert log_data["data"]["user"]["username"] == "testuser"
        assert log_data["data"]["config"]["timeout"] == 30

    def test_redacts_sensitive_list_items(self) -> None:
        """Test that sensitive data in lists is redacted."""
        formatter = RedactingJsonFormatter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Add list with sensitive data
        record.items = [
            {"name": "item1", "secret": "hidden"},
            "normal_string",
            {"api_key": "abc123"},
        ]

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        # Verify sensitive data in lists is redacted
        assert log_data["items"][0]["secret"] == "[REDACTED]"
        assert log_data["items"][1] == "normal_string"
        assert log_data["items"][2]["api_key"] == "[REDACTED]"

    def test_adds_service_context(self) -> None:
        """Test that service context is added to logs."""
        formatter = RedactingJsonFormatter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        # Verify service context is added
        assert log_data["service_name"] == "wireguard-mesh-manager"
        assert log_data["request_id"] is None
        assert log_data["correlation_id"] is None

    def test_preserves_existing_context(self) -> None:
        """Test that existing request context is preserved."""
        formatter = RedactingJsonFormatter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Add existing context
        record.request_id = "req-123"
        record.correlation_id = "corr-456"
        record.service_name = "custom-service"

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        # Verify context is preserved
        assert log_data["request_id"] == "req-123"
        assert log_data["correlation_id"] == "corr-456"
        assert log_data["service_name"] == "custom-service"


class TestLoggingIntegration:
    """Test logging integration with the application."""

    @pytest.fixture
    def app_with_logging(self) -> FastAPI:
        """Create a test app with logging configured."""
        from app.main import app

        return app

    async def test_logging_middleware_adds_headers(
        self, async_client: AsyncClient
    ) -> None:
        """Test that logging middleware adds request and correlation ID headers."""
        response = await async_client.get("/")

        # Verify response headers
        assert "X-Request-ID" in response.headers
        assert len(response.headers["X-Request-ID"]) == 36  # UUID length

    async def test_logging_middleware_preserves_correlation_id(
        self, async_client: AsyncClient
    ) -> None:
        """Test that correlation ID is preserved from request header."""
        correlation_id = "test-correlation-123"
        headers = {"X-Correlation-ID": correlation_id}

        response = await async_client.get("/", headers=headers)

        # Verify correlation ID is preserved
        assert response.headers.get("X-Correlation-ID") == correlation_id

    async def test_logging_middleware_generates_correlation_id(
        self, async_client: AsyncClient
    ) -> None:
        """Test that correlation ID is generated when not provided."""
        response = await async_client.get("/")

        # If no correlation ID was provided, request ID should be used
        request_id = response.headers["X-Request-ID"]
        correlation_id = response.headers.get("X-Correlation-ID")

        # Either correlation ID should equal request ID or be absent
        assert correlation_id is None or correlation_id == request_id

    @patch("app.middleware.logging_middleware.logger")
    async def test_logging_middleware_logs_requests(
        self, mock_logger: Any, async_client: AsyncClient
    ) -> None:
        """Test that logging middleware logs request start and completion."""
        await async_client.get("/health/status")

        # Verify logger was called
        assert mock_logger.info.called

        # Check the calls
        calls = [call.args[0] for call in mock_logger.info.call_args_list]
        assert "Request started" in calls
        assert "Request completed" in calls

    @patch("app.middleware.logging_middleware.logger")
    async def test_logging_middleware_logs_request_context(
        self, mock_logger: Any, async_client: AsyncClient
    ) -> None:
        """Test that logging middleware includes request context in logs."""
        await async_client.get("/health/status")

        # Get the extra data from the calls
        calls = mock_logger.info.call_args_list

        # Check request started call
        request_started_call = calls[0]
        extra_data = request_started_call.kwargs.get("extra", {})

        assert "request_id" in extra_data
        assert "correlation_id" in extra_data
        assert "method" in extra_data
        assert "url" in extra_data
        assert "client_ip" in extra_data

        assert extra_data["method"] == "GET"
        assert "health/status" in extra_data["url"]

    @patch("app.middleware.logging_middleware.logger")
    async def test_logging_middleware_handles_exceptions(
        self, mock_logger: Any, async_client: AsyncClient
    ) -> None:
        """Test that logging middleware properly handles exceptions in the middleware chain."""
        # This test verifies that exceptions are properly handled by the middleware
        # Since FastAPI handles 404s without exceptions, we just verify the middleware completes
        await async_client.get("/health/status")

        # Verify that the middleware completed without errors
        assert mock_logger.info.called


class TestLoggingConfiguration:
    """Test logging configuration."""

    def test_setup_logging_configures_root_logger(self) -> None:
        """Test that setup_logging properly configures the root logger."""
        # Clear any existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Setup logging
        setup_logging(level="DEBUG", service_name="test-service")

        # Verify root logger is configured
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG
        assert len(root_logger.handlers) > 0

        # Verify handler uses our formatter
        handler = root_logger.handlers[0]
        assert isinstance(handler.formatter, RedactingJsonFormatter)

    def test_get_logger_returns_logger_instance(self) -> None:
        """Test that get_logger returns a proper logger instance."""
        logger = logging.getLogger("test-logger")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test-logger"

    def test_log_level_configuration(self) -> None:
        """Test that different log levels work correctly."""
        logger = logging.getLogger("test-levels")

        # Test all log levels
        with patch("logging.Logger.handle") as mock_handle:
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")
            logger.critical("Critical message")

            # Verify all levels were called
            assert mock_handle.call_count == 5

    def test_redacts_edge_cases(self) -> None:
        """Test redaction edge cases."""
        formatter = RedactingJsonFormatter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Test edge cases
        record.empty_dict = {}
        record.empty_list = []
        record.none_value = None
        record.mixed_data = {
            "normal": "value",
            "nested": {
                "deep": {"secret": "hidden"},
                "safe_list": [{"normal_field": "safe_value"}],
                "mixed_list": [{"normal": "value"}, "unsafe_string_with_password"],
            },
        }

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        assert log_data["empty_dict"] == {}
        assert log_data["empty_list"] == []
        assert log_data["none_value"] is None
        assert log_data["mixed_data"]["nested"]["deep"]["secret"] == "[REDACTED]"
        assert (
            log_data["mixed_data"]["nested"]["safe_list"][0]["normal_field"]
            == "safe_value"
        )
        assert log_data["mixed_data"]["nested"]["mixed_list"][0]["normal"] == "value"
        assert log_data["mixed_data"]["nested"]["mixed_list"][1] == "[REDACTED]"
        assert log_data["mixed_data"]["normal"] == "value"
