import base64
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from cryptography.hazmat.primitives.asymmetric import ed25519

from .identity import Identity
from .topic import Topic

_ENCRYPTED_KEY = "_encrypted"


@dataclass(frozen=True)
class Message:
    """
    A cryptographically signed, immutable communication unit.

    Attributes:
        id (str): Unique message identifier.
        sender (str): Fingerprint of the sending agent.
        topics (List[Topic]): Topics this message is routed to.
        payload (Dict[str, Any]): The content of the message.
        task_id (Optional[str]): Reference to a specific task context.
        timestamp (int): Unix timestamp in milliseconds.
        signature (bytes): Ed25519 signature of the message content.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender: str = field(default_factory=str)
    recipient: str | None = None
    topics: list[Topic] = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)
    task_id: str | None = None
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))
    signature: bytes = b""

    def sign(self, identity: Identity) -> "Message":
        """
        Sign the message using the sender's identity.
        Returns a new Message instance with the signature populated.
        """
        if identity.fingerprint != self.sender and self.sender != "":
            # In a real implementation we might want to enforce that self.sender matches identity.fingerprint
            pass

        # We construct a canonical representation of the message to sign
        content_bytes = self._serialize_for_signing()

        # Identity must have private key to sign
        if identity.private_key is None:
            raise ValueError("Identity does not have a private key for signing")

        private_key = ed25519.Ed25519PrivateKey.from_private_bytes(identity.private_key)
        signature = private_key.sign(content_bytes)

        # Return a new object because Message is frozen
        # We can use object.__setattr__ to bypass frozen check if we were modifying, but better to return new
        # However, dataclass replace is better
        import dataclasses
        return dataclasses.replace(self, signature=signature, sender=identity.fingerprint)

    def verify(self, sender_public_key: bytes) -> bool:
        """
        Verify the message signature against the sender's public key.
        """
        if not self.signature:
            return False

        try:
            public_key = ed25519.Ed25519PublicKey.from_public_bytes(sender_public_key)
            content_bytes = self._serialize_for_signing()
            public_key.verify(self.signature, content_bytes)
            return True
        except Exception:
            return False

    def _serialize_for_signing(self) -> bytes:
        """
        Create a deterministic byte representation of the message content.
        Uses msgpack for canonical serialization. Excludes signature.
        """
        import msgpack

        data = {
            "id": self.id,
            "sender": self.sender,
            "recipient": self.recipient,
            "topics": [str(t) for t in self.topics],
            "payload": self.payload,
            "task_id": self.task_id,
            "timestamp": self.timestamp,
        }
        return msgpack.packb(data) or b""

    def to_bytes(self) -> bytes:
        """Serialize message to bytes using msgpack."""
        import msgpack

        data = self.to_dict()
        # Ensure signature is bytes
        data["signature"] = data.get("signature") or b""
        return msgpack.packb(data) or b""

    @classmethod
    def from_bytes(cls, data: bytes) -> "Message":
        """Deserialize message from msgpack bytes."""
        import msgpack

        unpacked = msgpack.unpackb(data)
        if isinstance(unpacked, dict):
            return cls.from_dict(unpacked)
        raise ValueError("Invalid message bytes")

    def to_dict(self) -> dict[str, Any]:
        import dataclasses
        return dataclasses.asdict(self)

    def encrypt_payload(self, key: bytes) -> "Message":
        """
        Encrypt the payload using AES-256-GCM.
        Returns a new Message with encrypted payload.
        Requires converge.extensions.crypto.symmetric.
        """
        from converge.extensions.crypto.symmetric import encrypt as sym_encrypt

        plaintext = json.dumps(self.payload).encode("utf-8")
        ciphertext = sym_encrypt(plaintext, key)
        enc_b64 = base64.b64encode(ciphertext).decode("ascii")
        new_payload = {_ENCRYPTED_KEY: enc_b64}
        import dataclasses
        return dataclasses.replace(self, payload=new_payload)

    def decrypt_payload(self, key: bytes) -> "Message":
        """
        Decrypt the payload if it was encrypted with encrypt_payload.
        Returns a new Message with decrypted payload.
        """
        if _ENCRYPTED_KEY not in self.payload:
            return self
        from converge.extensions.crypto.symmetric import decrypt as sym_decrypt

        enc_b64 = self.payload[_ENCRYPTED_KEY]
        ciphertext = base64.b64decode(enc_b64.encode("ascii"))
        plaintext = sym_decrypt(ciphertext, key)
        payload = json.loads(plaintext.decode("utf-8"))
        import dataclasses
        return dataclasses.replace(self, payload=payload)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Message":
        # Handle nested Topic objects
        topics_data = data.get("topics", [])
        topics = [Topic.from_dict(t) if isinstance(t, dict) else t for t in topics_data]
        data = dict(data)
        data["topics"] = topics
        data.setdefault("recipient", None)
        valid_keys = {"id", "sender", "recipient", "topics", "payload", "task_id", "timestamp", "signature"}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)
