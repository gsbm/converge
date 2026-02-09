from dataclasses import dataclass, field
from typing import Any

from converge.core.capability import Capability
from converge.core.store import Store
from converge.core.topic import Topic


@dataclass
class DiscoveryQuery:
    topics: list[Topic] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    trust_threshold: float = 0.0


@dataclass
class AgentDescriptor:
    id: str
    topics: list[Topic]
    capabilities: list[Capability]

    def to_dict(self) -> dict[str, Any]:
        """Serialize for persistence."""
        return {
            "id": self.id,
            "topics": [t.to_dict() for t in self.topics],
            "capabilities": [
                {
                    "name": c.name,
                    "version": c.version,
                    "description": c.description,
                    "constraints": c.constraints,
                    "costs": c.costs,
                    "latency_ms": c.latency_ms,
                }
                for c in self.capabilities
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentDescriptor":
        """Deserialize from stored dict."""
        topics = [Topic.from_dict(t) for t in data.get("topics", [])]
        caps_data = data.get("capabilities", [])
        capabilities = [
            Capability(
                name=c.get("name", ""),
                version=c.get("version", "1.0"),
                description=c.get("description", ""),
                constraints=c.get("constraints", {}),
                costs=c.get("costs", {}),
                latency_ms=c.get("latency_ms", 0),
            )
            for c in caps_data
        ]
        return cls(id=data.get("id", ""), topics=topics, capabilities=capabilities)


_DISCOVERY_PREFIX = "discovery:agent:"


class DiscoveryService:
    """
    Service for discovering agents based on queries.
    Persists AgentDescriptors in Store when provided.
    """
    def __init__(self, store: Store | None = None):
        self.descriptors: dict[str, AgentDescriptor] = {}
        self.store = store
        if store:
            self._load_from_store()

    def _load_from_store(self) -> None:
        """Load persisted descriptors from store."""
        if not self.store:
            return
        keys = self.store.list(_DISCOVERY_PREFIX)
        for key in keys:
            val = self.store.get(key)
            if isinstance(val, dict):
                try:
                    desc = AgentDescriptor.from_dict(val)
                    self.descriptors[desc.id] = desc
                except Exception:
                    pass

    def register(self, descriptor: AgentDescriptor) -> None:
        self.descriptors[descriptor.id] = descriptor
        if self.store:
            self.store.put(
                f"{_DISCOVERY_PREFIX}{descriptor.id}",
                descriptor.to_dict(),
            )

    def unregister(self, agent_id: str) -> None:
        if agent_id in self.descriptors:
            del self.descriptors[agent_id]
        if self.store:
            self.store.delete(f"{_DISCOVERY_PREFIX}{agent_id}")

    def query(self, query: DiscoveryQuery, candidates: list[AgentDescriptor]) -> list[AgentDescriptor]:
        """
        Filter a list of agent candidates based on a discovery query.

        Args:
            query (DiscoveryQuery): The criteria for discovery (topics, capabilities).
            candidates (List[AgentDescriptor]): The list of agents to search within.

        Returns:
            List[AgentDescriptor]: A list of agents that match the query criteria.
        """
        results = []
        for agent in candidates:
            # Check topics
            topic_match = True
            if query.topics:
                # Require intersection of topics
                agent_topic_ids = {str(t) for t in agent.topics}
                query_topic_ids = {str(t) for t in query.topics}
                if not agent_topic_ids.intersection(query_topic_ids):
                    topic_match = False

            # Check capabilities (support both Capability objects and str names from Agent)
            cap_match = True
            if query.capabilities:
                agent_caps: set[str] = set()
                for c in agent.capabilities:
                    name = c.name if hasattr(c, "name") else str(c)
                    agent_caps.add(name)
                # Must have ALL requested capabilities
                if not set(query.capabilities).issubset(agent_caps):
                    cap_match = False

            if topic_match and cap_match:
                results.append(agent)

        return results
