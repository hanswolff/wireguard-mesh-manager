"""Password validation utilities and policies."""

from __future__ import annotations

import re
from typing import Any


class PasswordStrength:
    """Password strength levels."""

    VERY_WEAK = 0
    WEAK = 1
    FAIR = 2
    GOOD = 3
    STRONG = 4


class PasswordPolicy:
    """Password policy requirements and validation."""

    # Minimum password requirements
    MIN_LENGTH = 12
    MAX_LENGTH = 128

    # Character requirements
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGITS = True
    REQUIRE_SPECIAL_CHARS = True

    # Special characters that are allowed/required
    SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:,.<>?"

    # Prevent common patterns
    FORBIDDEN_PATTERNS = [
        r"password",
        r"123456",
        r"qwerty",
        r"admin",
        r"master",
        r"welcome",
        r"login",
        r"letmein",
    ]

    # Prevent sequential characters
    FORBIDDEN_SEQUENTIAL = [
        "abcdefghijklmnopqrstuvwxyz",
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "0123456789",
    ]

    @classmethod
    def validate_password(cls, password: str) -> dict[str, Any]:
        """
        Validate a password against the policy.

        Args:
            password: The password to validate

        Returns:
            Dictionary with validation results:
            - is_valid: bool - Overall validation result
            - strength: int - Password strength (0-4)
            - score: int - Detailed score (0-100)
            - feedback: list[str] - List of issues and suggestions
        """
        feedback = []
        score = 0

        # Length validation
        length = len(password)
        if length < cls.MIN_LENGTH:
            feedback.append(
                f"Password must be at least {cls.MIN_LENGTH} characters long (current: {length})"
            )
        elif length >= cls.MIN_LENGTH:
            score += 20
            if length >= 16:
                score += 10  # Bonus for longer passwords

        if length > cls.MAX_LENGTH:
            feedback.append(f"Password must not exceed {cls.MAX_LENGTH} characters")
            return {
                "is_valid": False,
                "strength": PasswordStrength.VERY_WEAK,
                "score": 0,
                "feedback": feedback,
            }

        # Character type validation
        has_upper = bool(re.search(r"[A-Z]", password))
        has_lower = bool(re.search(r"[a-z]", password))
        has_digit = bool(re.search(r"\d", password))
        has_special = bool(re.search(r"[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]", password))

        if cls.REQUIRE_UPPERCASE and not has_upper:
            feedback.append("Password must contain at least one uppercase letter")
        elif has_upper:
            score += 15

        if cls.REQUIRE_LOWERCASE and not has_lower:
            feedback.append("Password must contain at least one lowercase letter")
        elif has_lower:
            score += 15

        if cls.REQUIRE_DIGITS and not has_digit:
            feedback.append("Password must contain at least one digit")
        elif has_digit:
            score += 15

        if cls.REQUIRE_SPECIAL_CHARS and not has_special:
            feedback.append(
                f"Password must contain at least one special character ({cls.SPECIAL_CHARS})"
            )
        elif has_special:
            score += 15

        # Forbidden patterns
        password_lower = password.lower()
        for pattern in cls.FORBIDDEN_PATTERNS:
            if re.search(pattern, password_lower):
                feedback.append(
                    f"Password contains common/forbidden pattern: {pattern}"
                )
                score -= 20

        # Sequential characters
        for seq in cls.FORBIDDEN_SEQUENTIAL:
            if seq.lower() in password_lower:
                feedback.append("Password contains sequential characters")
                score -= 15
                break

        # Repetitive characters
        if re.search(r"(.)\1{2,}", password):
            feedback.append("Password contains repetitive characters")
            score -= 10

        # Ensure score is within bounds
        score = max(0, min(100, score))

        # Determine strength level
        if score < 30:
            strength = PasswordStrength.VERY_WEAK
        elif score < 50:
            strength = PasswordStrength.WEAK
        elif score < 70:
            strength = PasswordStrength.FAIR
        elif score < 85:
            strength = PasswordStrength.GOOD
        else:
            strength = PasswordStrength.STRONG

        # Overall validation - must meet minimum requirements
        is_valid = (
            length >= cls.MIN_LENGTH
            and length <= cls.MAX_LENGTH
            and (not cls.REQUIRE_UPPERCASE or has_upper)
            and (not cls.REQUIRE_LOWERCASE or has_lower)
            and (not cls.REQUIRE_DIGITS or has_digit)
            and (not cls.REQUIRE_SPECIAL_CHARS or has_special)
            and all(
                not re.search(pattern, password_lower)
                for pattern in cls.FORBIDDEN_PATTERNS
            )
        )

        return {
            "is_valid": is_valid,
            "strength": strength,
            "score": score,
            "feedback": feedback,
        }

    @classmethod
    def get_password_requirements(cls) -> list[str]:
        """Get a list of password requirements for display to users."""
        requirements = []

        requirements.append(f"At least {cls.MIN_LENGTH} characters long")

        if cls.REQUIRE_UPPERCASE:
            requirements.append("At least one uppercase letter (A-Z)")

        if cls.REQUIRE_LOWERCASE:
            requirements.append("At least one lowercase letter (a-z)")

        if cls.REQUIRE_DIGITS:
            requirements.append("At least one digit (0-9)")

        if cls.REQUIRE_SPECIAL_CHARS:
            requirements.append(f"At least one special character ({cls.SPECIAL_CHARS})")

        return requirements

    @classmethod
    def get_strength_label(cls, strength: int) -> tuple[str, str]:
        """
        Get human-readable strength label and color.

        Args:
            strength: Password strength value (0-4)

        Returns:
            Tuple of (label, color_class)
        """
        strength_map = {
            PasswordStrength.VERY_WEAK: ("Very Weak", "text-red-600"),
            PasswordStrength.WEAK: ("Weak", "text-orange-600"),
            PasswordStrength.FAIR: ("Fair", "text-yellow-600"),
            PasswordStrength.GOOD: ("Good", "text-blue-600"),
            PasswordStrength.STRONG: ("Strong", "text-green-600"),
        }
        return strength_map.get(strength, ("Unknown", "text-gray-600"))
