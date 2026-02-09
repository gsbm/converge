"""Secure random utilities."""

import secrets


def secure_random_bytes(n: int) -> bytes:
    """
    Generate cryptographically secure random bytes.

    Args:
        n: Number of bytes to generate.

    Returns:
        Random bytes of length n.
    """
    return secrets.token_bytes(n)
