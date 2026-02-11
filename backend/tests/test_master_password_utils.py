"""Tests for master password utility functions."""

from __future__ import annotations

import pytest

from app.services.master_password import master_password_cache
from app.utils.master_password import (
    ensure_master_password_unlocked,
    get_master_password,
    with_master_password_cache,
)


class TestMasterPasswordUtils:
    """Test cases for master password utility functions."""

    def setup_method(self) -> None:
        """Set up test case with fresh cache."""
        master_password_cache.lock()

    def test_get_master_password_with_provided_password(self) -> None:
        """Test getting master password when password is provided."""
        password = "test_master_password_123"

        result = get_master_password(provided_password=password)

        assert result == password

    def test_get_master_password_from_cache(self) -> None:
        """Test getting master password from cache."""
        password = "test_master_password_123"
        master_password_cache.unlock(password)

        result = get_master_password()

        assert result == password

    def test_get_master_password_cache_preferred_over_provided(self) -> None:
        """Test that cache is preferred over provided password when both available."""
        cache_password = "cache_master_password_123"
        provided_password = "provided_master_password_456"

        master_password_cache.unlock(cache_password)

        # Should use cached password and verify provided matches
        # Since they don't match, it should raise an error
        with pytest.raises(
            ValueError, match="Provided master password does not match cached password"
        ):
            get_master_password(provided_password=provided_password)

    def test_get_master_password_provided_matches_cache(self) -> None:
        """Test when provided password matches cached password."""
        password = "test_master_password_123"
        master_password_cache.unlock(password)

        result = get_master_password(provided_password=password)

        assert result == password

    def test_get_master_password_no_cache_no_provided(self) -> None:
        """Test error when no password is available."""
        with pytest.raises(ValueError, match="Master password is required"):
            get_master_password()

    def test_get_master_password_require_cache_false(self) -> None:
        """Test get_master_password with require_cache=False."""
        password = "test_master_password_123"

        result = get_master_password(provided_password=password, require_cache=False)

        assert result == password

    def test_get_master_password_require_cache_true_locked(self) -> None:
        """Test get_master_password with require_cache=True when cache is locked."""
        password = "test_master_password_123"

        with pytest.raises(ValueError, match="Master password cache is not unlocked"):
            get_master_password(provided_password=password, require_cache=True)

    def test_get_master_password_require_cache_true_unlocked(self) -> None:
        """Test get_master_password with require_cache=True when cache is unlocked."""
        password = "test_master_password_123"
        master_password_cache.unlock(password)

        result = get_master_password(provided_password=None, require_cache=True)

        assert result == password

    def test_ensure_master_password_unlocked_new_unlock(self) -> None:
        """Test ensure_master_password_unlocked with new unlock."""
        password = "test_master_password_123"

        result = ensure_master_password_unlocked(password)

        assert result is True
        assert master_password_cache.is_unlocked is True
        assert master_password_cache.verify_password(password) is True

    def test_ensure_master_password_unlocked_already_unlocked_same_password(
        self,
    ) -> None:
        """Test ensure_master_password_unlocked when already unlocked with same password."""
        password = "test_master_password_123"
        master_password_cache.unlock(password)

        result = ensure_master_password_unlocked(password)

        assert result is True
        assert master_password_cache.is_unlocked is True

    def test_ensure_master_password_unlocked_already_unlocked_different_password(
        self,
    ) -> None:
        """Test ensure_master_password_unlocked when already unlocked with different password."""
        old_password = "old_master_password_123"
        new_password = "new_master_password_456"

        master_password_cache.unlock(old_password)

        result = ensure_master_password_unlocked(new_password)

        assert result is True
        assert master_password_cache.is_unlocked is True
        assert master_password_cache.verify_password(new_password) is True
        assert master_password_cache.verify_password(old_password) is False

    def test_ensure_master_password_unlocked_invalid_password(self) -> None:
        """Test ensure_master_password_unlocked with invalid password."""
        # This should succeed since any password is considered "valid" for unlocking
        password = "any_password"
        result = ensure_master_password_unlocked(password)

        assert result is True
        assert master_password_cache.is_unlocked is True

    def test_with_master_password_cache_decorator(self) -> None:
        """Test the with_master_password_cache decorator."""

        # Define a test function
        @with_master_password_cache
        def test_function(master_password: str) -> str:
            return f"processed_{master_password}"

        password = "test_master_password_123"

        # Test with provided password (no cache)
        result = test_function(master_password=password)
        assert result == f"processed_{password}"

        # Test with cached password
        master_password_cache.unlock(password)
        result = test_function(
            master_password=None
        )  # None should be resolved from cache
        assert result == f"processed_{password}"

        # Test with provided password that doesn't match cache
        with pytest.raises(
            ValueError, match="Provided master password does not match cached password"
        ):
            test_function(master_password="wrong_password")

    def test_with_master_password_cache_decorator_require_cache(self) -> None:
        """Test the with_master_password_cache decorator with require_cache=True."""

        @with_master_password_cache(require_cache=True)
        def test_function(master_password: str) -> str:
            return f"processed_{master_password}"

        password = "test_master_password_123"

        # Should fail when cache is locked
        with pytest.raises(ValueError, match="Master password cache is not unlocked"):
            test_function(master_password=password)

        # Should succeed when cache is unlocked
        master_password_cache.unlock(password)
        result = test_function(master_password=None)
        assert result == f"processed_{password}"

    def test_with_master_password_cache_decorator_custom_param_name(self) -> None:
        """Test the with_master_password_cache decorator with custom parameter name."""

        @with_master_password_cache(password_param_name="custom_password")
        def test_function(custom_password: str) -> str:
            return f"processed_{custom_password}"

        password = "test_master_password_123"
        result = test_function(custom_password=password)
        assert result == f"processed_{password}"

    def test_get_master_password_fallback_to_provided_on_cache_error(self) -> None:
        """Test fallback to provided password when cache access fails."""
        password = "test_master_password_123"

        # Mock cache to raise an exception on access
        original_is_unlocked = master_password_cache.is_unlocked
        original_get_master_password = master_password_cache.get_master_password

        try:
            # Simulate cache being "unlocked" but failing on get_master_password
            master_password_cache._is_locked = False  # type: ignore

            def mock_get_master_password():
                raise ValueError("Simulated cache error")

            master_password_cache.get_master_password = mock_get_master_password  # type: ignore

            # Should fall back to provided password
            result = get_master_password(provided_password=password)
            assert result == password

        finally:
            # Restore original state
            master_password_cache._is_locked = not original_is_unlocked  # type: ignore
            master_password_cache.get_master_password = original_get_master_password  # type: ignore
