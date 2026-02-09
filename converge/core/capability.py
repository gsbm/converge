from dataclasses import dataclass, field
from typing import Any


@dataclass
class Capability:
    """
    Defines a specific ability or tool an agent possesses.

    Attributes:
        name (str): Unique name of the capability.
        version (str): Semantic version string.
        description (str): Human-readable description.
        constraints (Dict[str, Any]): Usage limitations.
        costs (Dict[str, float]): Resource costs associated with usage.
        latency_ms (int): Expected execution latency.
    """
    name: str
    version: str
    description: str
    constraints: dict[str, Any] = field(default_factory=dict)
    costs: dict[str, float] = field(default_factory=dict)
    latency_ms: int = 0

@dataclass
class CapabilitySet:
    """
    A collection of capabilities possessed by an agent.
    """
    capabilities: list[Capability] = field(default_factory=list)

    def add(self, capability: Capability) -> None:
        """Add a capability to the set."""
        self.capabilities.append(capability)

    def has(self, name: str) -> bool:
        """Check if a capability exists by name."""
        return any(c.name == name for c in self.capabilities)
