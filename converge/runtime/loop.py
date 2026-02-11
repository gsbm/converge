import asyncio
import contextlib
import inspect
import logging
import time
from typing import TYPE_CHECKING, Any, cast

from converge.core.agent import Agent
from converge.network.transport.base import Transport
from converge.observability.tracing import trace

if TYPE_CHECKING:
    from converge.core.store import Store
    from converge.network.discovery import AgentDescriptor, DiscoveryService
    from converge.network.identity_registry import IdentityRegistry
    from converge.observability.metrics import MetricsCollector
    from converge.observability.replay import ReplayLog

logger = logging.getLogger(__name__)


class Inbox:
    """
    Buffers incoming messages for the agent.
    Supports bounded queue with configurable behavior when full.

    **Custom inbox:** Any object that implements ``async push(message)`` and
    ``poll(batch_size=10) -> list`` can be passed to AgentRuntime as ``inbox=``.
    """
    def __init__(self, maxsize: int | None = None, *, drop_when_full: bool = False):
        self._queue = asyncio.Queue(maxsize=maxsize or 0)
        self._drop_when_full = drop_when_full

    async def push(self, message: Any) -> None:
        if self._drop_when_full and self._queue.full():
            return
        await self._queue.put(message)

    def poll(self, batch_size: int = 10) -> list[Any]:
        """
        Get all currently available messages up to batch_size.
        Non-blocking.
        """
        messages = []
        try:
            while len(messages) < batch_size:
                messages.append(self._queue.get_nowait())
        except asyncio.QueueEmpty:
            pass
        return messages

class AgentRuntime:
    """
    Manages the execution loop of an agent.
    """

    def __init__(
        self,
        agent: Agent,
        transport: Transport,
        pool_manager=None,
        task_manager=None,
        metrics_collector: "MetricsCollector | None" = None,
        discovery_service: "DiscoveryService | None" = None,
        agent_descriptor: "AgentDescriptor | None" = None,
        identity_registry: "IdentityRegistry | None" = None,
        replay_log: "ReplayLog | None" = None,
        tool_registry=None,
        checkpoint_store: "Store | None" = None,
        checkpoint_interval_sec: float = 60.0,
        inbox=None,
        inbox_kwargs: dict[str, Any] | None = None,
        scheduler=None,
        executor_factory=None,
        executor_kwargs: dict[str, Any] | None = None,
    ):
        """
        Initialize the agent runtime.

        Args:
            agent: The agent instance.
            transport: Transport for sending and receiving messages.
            pool_manager: Optional pool manager for pool membership.
            task_manager: Optional task manager for task lifecycle.
            metrics_collector: Optional metrics collector.
            discovery_service: Optional discovery service. When set, the agent
                is registered on start() and unregistered on stop() so peers can
                discover it by topic/capability.
            agent_descriptor: Optional descriptor for discovery. If discovery_service
                is set and agent_descriptor is None, a descriptor is built from the
                agent (id, topics, capabilities) at start().
            identity_registry: Optional registry mapping agent fingerprints to public
                keys. When set, the runtime uses receive_verified() and drops messages
                that fail verification (log at debug). Populate from discovery or store
                to enable verified receive.
            replay_log: Optional replay log. When set, incoming messages (in
                _listen_transport) and outgoing messages (SendMessage in executor)
                are recorded for audit and replay.
            tool_registry: Optional ToolRegistry for InvokeTool decisions.
            checkpoint_store: Optional store for writing periodic checkpoints (agent_id -> last_activity_ts)
                for observability. Does not affect message replay; pool/task state is restored by
                using the same store for PoolManager and TaskManager on restart.
            checkpoint_interval_sec: Interval in seconds between checkpoint writes when checkpoint_store is set.
            inbox: Optional custom inbox. Must implement push(message) and poll(batch_size) -> list.
                If None, an Inbox is created with inbox_kwargs.
            inbox_kwargs: Optional dict of kwargs for the default Inbox when inbox is None (e.g. maxsize, drop_when_full).
            scheduler: Optional custom scheduler. Must implement notify() and wait_for_work(timeout) -> bool.
                If None, the default Scheduler() is used.
            executor_factory: Optional callable (agent_id, network, task_manager, pool_manager, **kwargs) -> Executor.
                When provided, the runtime calls it in the run loop to obtain the executor instead of building StandardExecutor.
                Use for custom executors or to inject extra dependencies.
            executor_kwargs: Optional dict of kwargs passed to StandardExecutor when executor_factory is not used
                (e.g. custom_handlers, safety_policy, bidding_protocols). Ignored if executor_factory is set.
        """
        self.agent = agent
        self.transport = transport
        if inbox is not None:
            self.inbox = inbox
        else:
            self.inbox = Inbox(**(inbox_kwargs or {}))
        self.running = False
        self._loop_task: asyncio.Task | None = None
        self._listen_task: asyncio.Task | None = None
        self.metrics_collector = metrics_collector
        self.discovery_service = discovery_service
        self.agent_descriptor = agent_descriptor
        self.identity_registry = identity_registry
        self.replay_log = replay_log
        self.tool_registry = tool_registry
        self.checkpoint_store = checkpoint_store
        self.checkpoint_interval_sec = checkpoint_interval_sec
        self._last_checkpoint_ts: float = 0.0
        self.executor_factory = executor_factory
        self.executor_kwargs = executor_kwargs or {}

        from .scheduler import Scheduler
        self.pool_manager = pool_manager
        self.task_manager = task_manager
        self.scheduler = Scheduler() if scheduler is None else scheduler

    async def start(self) -> None:
        """Start the agent loop."""
        if self.running:
            return

        self.running = True

        self.agent.on_start()

        await self.transport.start()

        # Register with discovery so peers can find this agent by topic/capability
        if self.discovery_service is not None:
            desc = self.agent_descriptor
            if desc is None:
                from converge.network.network import build_descriptor
                desc = build_descriptor(self.agent)
            self.discovery_service.register(desc)

        # Start listening for messages
        self._listen_task = asyncio.create_task(self._listen_transport())

        # Start main loop
        self._loop_task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        """Stop the agent loop."""
        self.running = False

        # Wake up scheduler so loop checks running flag
        if hasattr(self, 'scheduler'):
            self.scheduler.notify()

        if self._listen_task:
            self._listen_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._listen_task

        if self._loop_task:
            self._loop_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._loop_task

        await self.transport.stop()

        if self.discovery_service is not None:
            self.discovery_service.unregister(self.agent.id)

        self.agent.on_stop()

        self._loop_task = None
        self._listen_task = None

    async def _listen_transport(self) -> None:
        """Continuously receive messages from transport and push to inbox."""
        while self.running:
            try:
                if self.identity_registry is not None:
                    message = await self.transport.receive_verified(self.identity_registry)
                    if message is None:
                        logger.debug("Dropping unverified message (unknown sender or bad signature)")
                        continue
                else:
                    message = await self.transport.receive()
                if self.metrics_collector:
                    self.metrics_collector.inc("messages_received")
                if self.replay_log is not None:
                    self.replay_log.record_message(message)
                await self.inbox.push(message)
                self.scheduler.notify()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("Error receiving message: %s", e)
                await asyncio.sleep(1)

    async def _run_loop(self) -> None:
        """The main execution loop."""
        from converge.network.network import AgentNetwork

        from .executor import StandardExecutor

        # Setup executor if possible
        # We wrap transport in temporary network object if needed, or if we have one.
        # Ideally Runtime gets AgentNetwork, not just Transport.
        # For backward compatibility, we wrap.
        network = AgentNetwork(self.transport)

        # Just use inline logic using the new Executor class to prove separation
        # If managers are None, we can't fully execute some decisions, but that's existing behavior.
        # We need mock managers if None? Or just check inside Executor?
        # StandardExecutor assumes they exist.
        # Let's stick to a local helper that delegates to StandardExecutor if possible.

        if self.task_manager and self.pool_manager:
            if self.executor_factory is not None:
                executor = self.executor_factory(
                    self.agent.id,
                    network,
                    self.task_manager,
                    self.pool_manager,
                    metrics_collector=self.metrics_collector,
                    replay_log=self.replay_log,
                    tool_registry=self.tool_registry,
                )
            else:
                executor = StandardExecutor(
                    self.agent.id,
                    network,
                    self.task_manager,
                    self.pool_manager,
                    metrics_collector=self.metrics_collector,
                    replay_log=self.replay_log,
                    tool_registry=self.tool_registry,
                    **self.executor_kwargs,
                )
        else:
            executor = None

        while self.running:
            # 1. Wait for work (Event driven)
            # Wake up at least every few seconds for health checks or task polling if tasks aren't event-driven yet
            # (Tasks usually come from messages or internal generation)
            await self.scheduler.wait_for_work(timeout=1.0)

            if not self.running:
                break

            # 2. Poll inbox
            messages = self.inbox.poll()

            # 3. Poll task queue (scoped by pool/capabilities when pool_manager is set)
            tasks: list[Any] = []
            if self.task_manager is not None:
                if self.pool_manager is not None:
                    pool_ids = self.pool_manager.get_pools_for_agent(self.agent.id)
                    capabilities = getattr(self.agent, "capabilities", None) or []
                    tasks = self.task_manager.list_pending_tasks_for_agent(
                        self.agent.id,
                        pool_ids=pool_ids,
                        capabilities=capabilities,
                    )
                else:
                    tasks = self.task_manager.list_pending_tasks()

            # 4. Decide
            if messages or tasks:
                self.agent.on_tick(messages, tasks)
                with trace("agent.decide"):
                    if inspect.iscoroutinefunction(self.agent.decide):
                        decisions = cast(list[Any], await self.agent.decide(messages, tasks))
                    else:
                        decisions = cast(list[Any], self.agent.decide(messages, tasks))

                # 5. Execute
                if decisions:
                    with trace("executor.execute"):
                        if executor:
                            await executor.execute(decisions)
                        else:
                            for decision in decisions:
                                await self._execute_decision_fallback(decision)

            # Optional checkpoint for observability (pool/task state restored via same store on restart)
            if self.checkpoint_store is not None:
                now = time.monotonic()
                if now - self._last_checkpoint_ts >= self.checkpoint_interval_sec:
                    try:
                        self.checkpoint_store.put(
                            f"checkpoint:{self.agent.id}",
                            {"last_activity_ts": time.time()},
                        )
                        self._last_checkpoint_ts = now
                    except Exception as e:
                        logger.debug("Checkpoint write skipped: %s", e)

    async def _execute_decision_fallback(self, decision: Any) -> None:
        # Legacy fallback if no executor configured
        if hasattr(decision, 'sender'): # Message
             if not decision.signature:
                 decision = self.agent.sign_message(decision)
             await self.transport.send(decision)
