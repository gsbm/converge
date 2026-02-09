"""Tests for converge.core.message."""

import msgpack
import pytest

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
