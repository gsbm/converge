from converge.core.agent import Agent
from converge.core.message import Message
from converge.network.discovery import AgentDescriptor, DiscoveryQuery
from converge.network.transport.base import Transport


class AgentNetwork:
    """
    Manages agent registration and message routing.
    """
    def __init__(self, transport: Transport):
        self.transport = transport
        self.local_agents: dict[str, Agent] = {}

    def register_agent(self, agent: Agent) -> None:
        self.local_agents[agent.id] = agent

    def unregister_agent(self, agent_id: str) -> None:
        if agent_id in self.local_agents:
            del self.local_agents[agent_id]

    async def send(self, message: Message) -> None:
        await self.transport.send(message)

    async def broadcast(self, message: Message) -> None:
        # In a real p2p network this would flood or use gossip
        # For now, we reuse send, assuming transport handles broadcast semantics or destination
        await self.transport.send(message)

    def discover(self, query: DiscoveryQuery) -> list[AgentDescriptor]:
        from converge.network.discovery import DiscoveryService

        # Build descriptors from local agents
        candidates = []
        for agent in self.local_agents.values():
            # Agents might not explicitly list topics/capabilities in a way we track yet
            # For now, let's assume agent.capabilities is available.
            # Topics? Agent might subscribe to topics, but does it "own" them?
            # Let's assume yes for discovery purposes (e.g. what it listens to).
            # We don't have a standard way to get agent topics yet.
            # Let's assume agent has a .topics attribute or we skip topics for now.

            # Temporary: introspect or default
            topics = getattr(agent, 'topics', [])
            caps = getattr(agent, 'capabilities', [])

            candidates.append(AgentDescriptor(
                id=agent.id,
                topics=topics,
                capabilities=caps,
            ))

        service = DiscoveryService()
        return service.query(query, candidates)
