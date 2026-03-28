"""Tests for converge.core.message."""

import msgpack
import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519

from converge.core.identity import Identity
from converge.core.message import Message
from converge.core.topic import Topic


def test_message_signing_verification():
    sender = Identity.generate()
    receiver = Identity.generate()

    topic = Topic(namespace="test", attributes={"type": "ping"})
    msg = Message(sender=sender.fingerprint, topics=[topic], payload={"content": "hello"})

    signed_msg = msg.sign(sender)
    assert signed_msg.signature
    assert signed_msg.verify(sender.public_key)
    assert not signed_msg.verify(receiver.public_key)


def test_message_sign_verify_errors():
    identity = Identity.generate()
    msg = Message(sender="other_fingerprint")

    msg.sign(identity)

    id_public_only = Identity(
        public_key=identity.public_key, private_key=None, fingerprint=identity.fingerprint,
    )
    with pytest.raises(ValueError, match="private key"):
        msg.sign(id_public_only)

    assert not msg.verify(identity.public_key)


def test_message_to_bytes_from_bytes():
    msg = Message(sender="s1", payload={"x": 1})
    data = msg.to_bytes()
    assert isinstance(data, bytes)
    restored = Message.from_bytes(data)
    assert restored.sender == msg.sender
    assert restored.payload == msg.payload


def test_message_from_bytes_invalid():
    with pytest.raises(ValueError, match="Invalid"):
        Message.from_bytes(msgpack.packb([1, 2, 3]))


def test_message_encrypt_decrypt_payload():
    msg = Message(sender="s1", payload={"secret": "data"})
    key = b"0" * 32
    enc = msg.encrypt_payload(key)
    assert "_encrypted" in enc.payload
    dec = enc.decrypt_payload(key)
    assert dec.payload == {"secret": "data"}


def test_message_decrypt_payload_not_encrypted():
    msg = Message(sender="s1", payload={"plain": 1})
    key = b"0" * 32
    result = msg.decrypt_payload(key)
    assert result is msg


def test_message_signing_canonical_payload_order():
    sender = Identity.generate()
    payload_a = {"b": 2, "a": {"z": 1, "y": 2}}
    payload_b = {"a": {"y": 2, "z": 1}, "b": 2}
    m1 = Message(sender=sender.fingerprint, payload=payload_a).sign(sender)
    m2 = Message(
        id=m1.id,
        sender=sender.fingerprint,
        payload=payload_b,
        task_id=m1.task_id,
        timestamp=m1.timestamp,
        topics=m1.topics,
        recipient=m1.recipient,
    ).sign(sender)
    assert m1.signature == m2.signature


def test_message_signing_compatibility_vector():
    """
    Compatibility vector for deterministic signing bytes.

    This protects cross-version verification behavior.
    """
    private_key = bytes.fromhex("1f" * 32)
    sk = ed25519.Ed25519PrivateKey.from_private_bytes(private_key)
    public_key = sk.public_key().public_bytes_raw()
    identity = Identity.from_public_key(public_key)
    identity = Identity(public_key=identity.public_key, private_key=private_key, fingerprint=identity.fingerprint)

    msg = Message(
        id="msg-fixed-001",
        sender=identity.fingerprint,
        payload={"b": 2, "a": {"z": 1, "y": 2}},
        timestamp=1700000000000,
    ).sign(identity)

    expected_sig_hex = (
        "c68853863eac5d9371772d11d12d4356bb341d97934858e4667d76b3dc8f7169"
        "5c44cb20a55a757bad792d36885ee41f67391c9e733fd0d498de788126f37e08"
    )
    assert msg.signature.hex() == expected_sig_hex
