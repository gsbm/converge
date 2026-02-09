"""Key derivation utilities."""

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def derive_key(
    password: str,
    salt: bytes,
    length: int = 32,
    iterations: int = 100_000,
) -> bytes:
    """
    Derive a key from a password using PBKDF2-HMAC-SHA256.

    Args:
        password: The password to derive from.
        salt: Random salt (at least 16 bytes recommended).
        length: Desired key length in bytes.
        iterations: Number of PBKDF2 iterations.

    Returns:
        Derived key bytes of the specified length.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=length,
        salt=salt,
        iterations=iterations,
    )
    return kdf.derive(password.encode("utf-8"))
