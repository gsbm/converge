"""Registry mapping agent fingerprints to public keys for message verification."""


class IdentityRegistry:
    """
    Maps agent IDs (fingerprints) to Ed25519 public keys.
    Used by transports to verify message signatures.
    """

    def __init__(self) -> None:
        self._registry: dict[str, bytes] = {}

    def register(self, agent_id: str, public_key: bytes) -> None:
        """Register an agent's public key."""
        self._registry[agent_id] = public_key

    def unregister(self, agent_id: str) -> None:
        """Remove an agent from the registry."""
        self._registry.pop(agent_id, None)

    def get(self, agent_id: str) -> bytes | None:
        """Get the public key for an agent, or None if not found."""
        return self._registry.get(agent_id)

    def __contains__(self, agent_id: str) -> bool:
        return agent_id in self._registry
