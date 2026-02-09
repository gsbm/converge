"""Symmetric encryption utilities using AES-256-GCM."""

import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def encrypt(plaintext: bytes, key: bytes, associated_data: bytes | None = None) -> bytes:
    """
    Encrypt plaintext with AES-256-GCM.

    Args:
        plaintext: Data to encrypt.
        key: 32-byte encryption key.
        associated_data: Optional authenticated associated data (not encrypted).

    Returns:
        nonce (12 bytes) + ciphertext + tag (16 bytes), concatenated.
    """
    if len(key) != 32:
        raise ValueError("Key must be 32 bytes for AES-256")
    aesgcm = AESGCM(key)
    nonce = secrets.token_bytes(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data or b"")
    return nonce + ciphertext


def decrypt(ciphertext: bytes, key: bytes, associated_data: bytes | None = None) -> bytes:
    """
    Decrypt AES-256-GCM ciphertext.

    Args:
        ciphertext: nonce (12 bytes) + encrypted data + tag (16 bytes).
        key: 32-byte decryption key.
        associated_data: Same as used for encryption, if any.

    Returns:
        Decrypted plaintext.
    """
    if len(key) != 32:
        raise ValueError("Key must be 32 bytes for AES-256")
    if len(ciphertext) < 12 + 16:
        raise ValueError("Ciphertext too short")
    nonce = ciphertext[:12]
    actual_ct = ciphertext[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, actual_ct, associated_data or b"")
