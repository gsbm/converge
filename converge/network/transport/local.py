import asyncio

from converge.core.message import Message

from .base import Transport


class LocalTransportRegistry:
    """
    Shared registry for local transports to find each other.
    Supports point-to-point (recipient) and topic-based routing.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.queues = {}
            cls._instance.topic_subscriptions = {}
        return cls._instance

    def register(self, agent_id: str, queue: asyncio.Queue) -> None:
        self.queues[agent_id] = queue

    def unregister(self, agent_id: str) -> None:
        if agent_id in self.queues:
            del self.queues[agent_id]
        self.topic_subscriptions.pop(agent_id, None)

    def get_queue(self, agent_id: str) -> asyncio.Queue | None:
        return self.queues.get(agent_id)

    def subscribe(self, agent_id: str, topic_namespace: str) -> None:
        if agent_id not in self.topic_subscriptions:
            self.topic_subscriptions[agent_id] = set()
        self.topic_subscriptions[agent_id].add(topic_namespace)

    def unsubscribe(self, agent_id: str, topic_namespace: str) -> None:
        if agent_id in self.topic_subscriptions:
            self.topic_subscriptions[agent_id].discard(topic_namespace)

    def get_subscribers_for_topics(self, topic_namespaces: list[str]) -> set[str]:
        subscribers = set()
        for agent_id, namespaces in self.topic_subscriptions.items():
            if namespaces & set(topic_namespaces):
                subscribers.add(agent_id)
        return subscribers

    def clear(self) -> None:
        """Clear all registered queues (useful for testing)."""
        self.queues.clear()
        self.topic_subscriptions.clear()


class LocalTransport(Transport):
    """
    Transport for in-process memory communication.
    """
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.queue: asyncio.Queue = asyncio.Queue()
        self.registry = LocalTransportRegistry()
        self._started = False

    async def start(self) -> None:
        self.registry.register(self.agent_id, self.queue)
        self._started = True

    async def stop(self) -> None:
        self.registry.unregister(self.agent_id)
        self._started = False

    async def send(self, message: Message) -> None:
        if not self._started:
            raise RuntimeError("Transport not started")

        targets: set[str] = set()

        if message.recipient:
            targets.add(message.recipient)
        elif message.topics:
            topic_namespaces = [t.namespace for t in message.topics]
            targets = self.registry.get_subscribers_for_topics(topic_namespaces)
            if not targets:
                targets = set(self.registry.queues.keys())
        else:
            targets = set(self.registry.queues.keys())

        for agent_id in targets:
            if agent_id == self.agent_id and not message.recipient:
                continue
            q = self.registry.get_queue(agent_id)
            if q is not None:
                await q.put(message)

    async def receive(self) -> Message:
        if not self._started:
            raise RuntimeError("Transport not started")
        return await self.queue.get()
