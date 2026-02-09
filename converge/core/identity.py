import hashlib
from dataclasses import dataclass

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519


@dataclass(frozen=True)
class Identity:
    """
    Cryptographic identity for an agent.

    Serves as the root of trust for an agent, enabling message signing and verification.
    Identities are immutable and derived from Ed25519 keypairs.

    Attributes:
        public_key (bytes): Raw Ed25519 public key.
        private_key (Optional[bytes]): Raw Ed25519 private key (None if verifying others).
        fingerprint (str): Hex-encoded SHA-256 hash of the public key.
    """
    public_key: bytes
    private_key: bytes | None
    fingerprint: str

    @classmethod
    def generate(cls) -> "Identity":
        """
        Generate a new random identity using Ed25519.

        Returns:
            Identity: A new identity with both public and private keys.
        """
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        # Serialize keys to bytes
        private_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

        # Create fingerprint (SHA-256 of public key)
        fingerprint = hashlib.sha256(public_bytes).hexdigest()

        return cls(
            public_key=public_bytes,
            private_key=private_bytes,
            fingerprint=fingerprint,
        )

    @classmethod
    def from_public_key(cls, public_key_bytes: bytes) -> "Identity":
        """
        Create an identity from a known public key (e.g. for verifying others).

        Args:
            public_key_bytes (bytes): The raw public key bytes.

        Returns:
            Identity: An identity instance (without private key).
        """
        fingerprint = hashlib.sha256(public_key_bytes).hexdigest()
        return cls(
            public_key=public_key_bytes,
            private_key=None,
            fingerprint=fingerprint,
        )
