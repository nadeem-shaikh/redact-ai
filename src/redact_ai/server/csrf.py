"""CSRF token management (BUILD_SPEC §14.2)."""

from __future__ import annotations

import secrets

COOKIE_NAME: str = "rai_csrf"
HEADER_NAME: str = "x-redact-csrf"
META_NAME: str = "rai-csrf"


def generate_token() -> str:
    """Return a fresh urlsafe-base64 32-byte token."""
    return secrets.token_urlsafe(32)


def token_matches(expected: str | None, presented: str | None) -> bool:
    if not expected or not presented:
        return False
    return secrets.compare_digest(expected, presented)
