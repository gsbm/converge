"""Tests for converge.extensions.crypto."""

import pytest

from converge.extensions.crypto import decrypt, derive_key, encrypt, secure_random_bytes


def test_encrypt_decrypt_roundtrip():
    key = secure_random_bytes(32)
    plain = b"secret data"
    ct = encrypt(plain, key)
    dec = decrypt(ct, key)
    assert dec == plain


def test_encrypt_decrypt_with_associated_data():
    key = secure_random_bytes(32)
    plain = b"data"
    aad = b"associated"
    ct = encrypt(plain, key, associated_data=aad)
    dec = decrypt(ct, key, associated_data=aad)
    assert dec == plain


def test_decrypt_wrong_key_fails():
    key = secure_random_bytes(32)
    ct = encrypt(b"x", key)
    wrong_key = secure_random_bytes(32)
    with pytest.raises(Exception):
        decrypt(ct, wrong_key)


def test_encrypt_wrong_key_length_raises():
    with pytest.raises(ValueError, match="32 bytes"):
        encrypt(b"x", b"short")


def test_decrypt_key_wrong_length():
    key = secure_random_bytes(32)
    ct = encrypt(b"x", key)
    with pytest.raises(ValueError, match="32 bytes"):
        decrypt(ct, b"short")
    with pytest.raises(ValueError, match="Ciphertext too short"):
        decrypt(b"x" * 10, key)


def test_derive_key_deterministic():
    pw = "password"
    salt = secure_random_bytes(16)
    k1 = derive_key(pw, salt)
    k2 = derive_key(pw, salt)
    assert k1 == k2


def test_derive_key_different_passwords():
    salt = secure_random_bytes(16)
    k1 = derive_key("pw1", salt)
    k2 = derive_key("pw2", salt)
    assert k1 != k2


def test_derive_key_different_salts():
    k1 = derive_key("pw", b"a" * 16)
    k2 = derive_key("pw", b"b" * 16)
    assert k1 != k2


def test_derive_key_length():
    k = derive_key("pw", secure_random_bytes(16), length=64)
    assert len(k) == 64


def test_secure_random_bytes_length():
    data = secure_random_bytes(32)
    assert len(data) == 32
