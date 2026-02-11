"""Utilities for master password integration with existing services."""

from __future__ import annotations

from app.services.master_password import get_master_password_cache
from app.utils.logging import get_logger

logger = get_logger(__name__)


def get_master_password(
    provided_password: str | None = None,
    require_cache: bool = False,
    session_id: str | None = None,
) -> str:
    """Get master password from cache or use provided password.

    This utility function provides a unified way for services to access
    the master password, with support for both cached and provided passwords.

    Args:
        provided_password: Master password provided in the request (optional)
        require_cache: If True, require the password to come from cache

    Returns:
        The master password to use

    Raises:
        ValueError: If no master password is available
    """
    # If cache is required and not unlocked, raise error
    master_password_cache = get_master_password_cache(session_id)
    if require_cache and not master_password_cache.is_unlocked:
        logger.warning("Master password cache is required but not unlocked")
        raise ValueError("Master password cache is not unlocked")

    # Try to get from cache first
    if master_password_cache.is_unlocked:
        # If a provided password exists, verify it matches the cache first
        if provided_password:
            if not master_password_cache.verify_password(provided_password):
                logger.warning(
                    "Provided master password does not match cached password"
                )
                raise ValueError(
                    "Provided master password does not match cached password"
                )
            logger.debug("Provided master password verified against cache")

        try:
            cached_password = master_password_cache.get_master_password()
            logger.debug("Using master password from cache")
            return cached_password
        except ValueError as e:
            logger.warning(
                "Failed to get master password from cache", extra={"error": str(e)}
            )
            if require_cache:
                raise
            # Fall back to provided password if cache access fails
            logger.info("Falling back to provided master password")

    # Use provided password if cache is not available
    if provided_password:
        logger.debug("Using provided master password")
        return provided_password

    # No password available
    logger.error("No master password available (cache locked and none provided)")
    raise ValueError(
        "Master password is required but not provided and cache is not unlocked"
    )


def ensure_master_password_unlocked(master_password: str) -> bool:
    """Ensure the master password cache is unlocked with the given password.

    This is a convenience function for services that need to ensure
    the cache is unlocked before proceeding.

    Args:
        master_password: Master password to unlock the cache with

    Returns:
        True if cache is unlocked (either was already unlocked or just unlocked)

    Raises:
        ValueError: If master password is invalid
    """
    master_password_cache = get_master_password_cache()
    if master_password_cache.is_unlocked:
        # Verify the cached password matches
        if master_password_cache.verify_password(master_password):
            return True
        else:
            logger.warning("Cached master password does not match provided password")
            # Cache has different password, so we need to re-lock and unlock
            master_password_cache.lock()

    # Unlock with the provided password
    success = master_password_cache.unlock(master_password)
    if not success:
        logger.error("Failed to unlock master password cache")
        raise ValueError("Failed to unlock master password cache")

    logger.info("Master password cache unlocked successfully")
    return True


def with_master_password_cache(
    func=None,
    *,
    password_param_name: str = "master_password",
    require_cache: bool = False,
):
    """Decorator to automatically handle master password retrieval.

    This decorator wraps a function to automatically get the master password
    from cache or use the provided password parameter.

    Args:
        func: Function to wrap (optional, for when called as @decorator)
        password_param_name: Name of the master password parameter
        require_cache: If True, require password to come from cache

    Returns:
        Wrapped function that handles master password automatically
    """

    def decorator(f):
        def wrapper(*args, **kwargs):
            # Extract master password from kwargs if provided
            provided_password = kwargs.get(password_param_name)

            # Get the master password using the utility
            master_password = get_master_password(
                provided_password=provided_password,
                require_cache=require_cache,
            )

            # Update kwargs with the resolved password
            kwargs[password_param_name] = master_password

            # Call the original function
            return f(*args, **kwargs)

        return wrapper

    # Handle both @decorator and @decorator() usage patterns
    if func is None:
        return decorator
    else:
        return decorator(func)
