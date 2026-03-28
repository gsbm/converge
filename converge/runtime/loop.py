import asyncio
import contextlib
import inspect
import logging
import time
from typing import TYPE_CHECKING, Any, cast

from converge.core.agent import Agent
from converge.network.network import AgentNetwork
from converge.network.transport.base import Transport
from converge.observability.tracing import trace

if TYPE_CHECKING:
    from converge.core.store import Store
    from converge.network.discovery import AgentDescriptor, DiscoveryService
    from converge.network.identity_registry import IdentityRegistry
    from converge.observability.metrics import MetricsCollector
    from converge.observability.replay import ReplayLog
    from converge.observability.runtime_ops import RuntimeOpsServer
    from converge.runtime.hooks import RuntimeHook

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
        health_check=None,
        ready_check=None,
        receive_timeout_sec: float | None = 30.0,
        claim_ttl_interval_sec: float | None = None,
        task_poll_interval_sec: float | None = None,
        max_tool_loop_iterations: int = 5,
        scheduler_timeout_sec: float = 1.0,
        task_refresh_interval_sec: float | None = 0.5,
        pool_cache_ttl_sec: float | None = 1.0,
        *,
        network: AgentNetwork | None = None,
        ops_server: "RuntimeOpsServer | None" = None,
        runtime_hooks: list["RuntimeHook"] | None = None,
        allow_network_transport_mismatch: bool = False,
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
                (e.g. custom_handlers, safety_policy, bidding_protocols, tool_timeout_sec, tool_allowlist).
                Ignored if executor_factory is set.
            health_check: Optional callable () -> bool. When set, is_healthy() delegates to it.
                Optionally expose via RuntimeOpsServer helper.
            ready_check: Optional callable () -> bool. When set, is_ready() delegates to it.
            receive_timeout_sec: Optional timeout for transport.receive() so the loop can react to
                shutdown. When set, receive() is called with this timeout; TimeoutError is caught and
                the loop continues. None means no timeout (block until message).
            claim_ttl_interval_sec: Optional interval in seconds. When set and task_manager is set,
                the run loop calls task_manager.release_expired_claims(time.monotonic()) at most
                once per interval so expired task claims are released automatically. Ignored if
                task_manager is None.
            task_poll_interval_sec: Optional interval in seconds. When set and task_manager is set,
                a background task periodically checks whether the set of pending tasks for this
                agent has changed and calls scheduler.notify() so the main loop wakes and processes
                tasks sooner. Ignored if task_manager is None.
            max_tool_loop_iterations: Max ReAct tool loop iterations (run InvokeTool, feed result back to decide). 0 disables.
            scheduler_timeout_sec: Max seconds to wait in scheduler.wait_for_work() before periodic wake.
            task_refresh_interval_sec: Optional interval for refreshing task visibility from shared store
                when polling for tasks. None disables periodic refresh (cache-only reads).
            pool_cache_ttl_sec: Optional TTL for cached pool membership lookups. None disables caching.
            network: Optional injected AgentNetwork. When None, runtime builds AgentNetwork(transport).
            ops_server: Optional RuntimeOpsServer helper. When set, runtime starts/stops it with lifecycle.
            runtime_hooks: Optional runtime hooks for fallback send and unverified receive drop.
            allow_network_transport_mismatch: If False and network is provided, require network.transport
                to be the same object as transport.
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
        self._health_check = health_check
        self._ready_check = ready_check
        self.receive_timeout_sec = receive_timeout_sec
        self.claim_ttl_interval_sec = claim_ttl_interval_sec
        self.task_poll_interval_sec = task_poll_interval_sec
        self.max_tool_loop_iterations = max_tool_loop_iterations
        self.scheduler_timeout_sec = scheduler_timeout_sec
        self.task_refresh_interval_sec = task_refresh_interval_sec
        self.pool_cache_ttl_sec = pool_cache_ttl_sec
        self._last_claim_ttl_ts: float = 0.0
        self._task_poll_task: asyncio.Task | None = None
        self._last_pending_task_ids: frozenset[str] | None = None
        self._last_task_refresh_ts: float = 0.0
        self._cached_pool_ids: list[str] | None = None
        self._pool_cache_ts: float = 0.0
        self.ops_server = ops_server
        self.runtime_hooks = runtime_hooks or []
        self.network = network
        if (
            self.network is not None
            and not allow_network_transport_mismatch
            and getattr(self.network, "transport", None) is not self.transport
        ):
            raise ValueError("Injected network transport does not match runtime transport")

        from .scheduler import Scheduler
        self.pool_manager = pool_manager
        self.task_manager = task_manager
        self.scheduler = Scheduler() if scheduler is None else scheduler
        self.coordination_metrics = None
        if self.metrics_collector is not None:
            from converge.observability.coordination_metrics import CoordinationMetrics

            self.coordination_metrics = CoordinationMetrics(self.metrics_collector)
            if self.pool_manager is not None and getattr(self.pool_manager, "coordination_metrics", None) is None:
                self.pool_manager.coordination_metrics = self.coordination_metrics
            if self.task_manager is not None and getattr(self.task_manager, "coordination_metrics", None) is None:
                self.task_manager.coordination_metrics = self.coordination_metrics

    def is_healthy(self) -> bool:
        """Return health status. Delegates to health_check callable if set, else True."""
        if self._health_check is not None:
            return self._health_check()
        return True

    def is_ready(self) -> bool:
        """Return readiness status. Delegates to ready_check callable if set, else True."""
        if self._ready_check is not None:
            return self._ready_check()
        return True

    async def start(self) -> None:
        """Start the agent loop."""
        if self.running:
            return

        self.running = True

        self.agent.on_start()

        await self.transport.start()
        if self.ops_server is not None:
            self.ops_server.start()

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

        if self.task_poll_interval_sec is not None and self.task_manager is not None:
            self._task_poll_task = asyncio.create_task(self._task_poll_loop())

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

        if self._task_poll_task:
            self._task_poll_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task_poll_task

        await self.transport.stop()
        if self.ops_server is not None:
            self.ops_server.stop()

        if self.discovery_service is not None:
            self.discovery_service.unregister(self.agent.id)

        self.agent.on_stop()

        self._loop_task = None
        self._listen_task = None
        self._task_poll_task = None

    async def _listen_transport(self) -> None:
        """Continuously receive messages from transport and push to inbox."""
        while self.running:
            try:
                timeout = self.receive_timeout_sec
                if self.identity_registry is not None:
                    message = await self.transport.receive_verified(
                        self.identity_registry,
                        timeout=timeout,
                    )
                    if message is None:
                        for hook in self.runtime_hooks:
                            callback = getattr(hook, "on_unverified_drop", None)
                            if not callable(callback):
                                continue
                            try:
                                callback({"agent_id": self.agent.id})
                            except Exception:
                                logger.debug("runtime hook on_unverified_drop failed", exc_info=True)
                        logger.debug("Dropping unverified message (unknown sender or bad signature)")
                        continue
                else:
                    message = await self.transport.receive(timeout=timeout)
                if self.metrics_collector:
                    self.metrics_collector.inc("messages_received")
                if self.replay_log is not None:
                    self.replay_log.record_inbound(
                        message,
                        agent_id=self.agent.id,
                        transport=type(self.transport).__name__,
                    )
                await self.inbox.push(message)
                self.scheduler.notify()
            except asyncio.CancelledError:
                break
            except TimeoutError:
                # Receive timeout: loop again to check running flag
                continue
            except Exception as e:
                logger.warning("Error receiving message: %s", e)
                await asyncio.sleep(1)

    async def _task_poll_loop(self) -> None:
        """Periodically check for pending task changes and notify scheduler to wake the main loop."""
        interval = self.task_poll_interval_sec
        if interval is None or self.task_manager is None:
            return
        try:
            while self.running:
                await asyncio.sleep(interval)
                if not self.running:
                    break
                if self.task_manager is None:
                    continue
                tasks = self._get_visible_tasks(force_refresh=True)
                current_ids = frozenset(t.id for t in tasks)
                if (
                    self._last_pending_task_ids is not None
                    and current_ids != self._last_pending_task_ids
                ):
                    self.scheduler.notify()
                self._last_pending_task_ids = current_ids
        except asyncio.CancelledError:
            pass

    def _should_refresh_tasks(self, *, force: bool = False) -> bool:
        if force:
            self._last_task_refresh_ts = time.monotonic()
            return True
        if self.task_refresh_interval_sec is None:
            return False
        now = time.monotonic()
        if now - self._last_task_refresh_ts >= self.task_refresh_interval_sec:
            self._last_task_refresh_ts = now
            return True
        return False

    def _get_pool_ids_for_agent(self, *, force: bool = False) -> list[str]:
        if self.pool_manager is None:
            return []
        if self.pool_cache_ttl_sec is None:
            return self.pool_manager.get_pools_for_agent(self.agent.id)
        now = time.monotonic()
        if (
            not force
            and self._cached_pool_ids is not None
            and now - self._pool_cache_ts < self.pool_cache_ttl_sec
        ):
            return self._cached_pool_ids
        pool_ids = self.pool_manager.get_pools_for_agent(self.agent.id)
        self._cached_pool_ids = pool_ids
        self._pool_cache_ts = now
        return pool_ids

    def _invalidate_pool_cache(self) -> None:
        self._cached_pool_ids = None
        self._pool_cache_ts = 0.0

    def _get_visible_tasks(self, *, force_refresh: bool = False) -> list[Any]:
        if self.task_manager is None:
            return []
        refresh = self._should_refresh_tasks(force=force_refresh)
        if self.pool_manager is not None:
            pool_ids = self._get_pool_ids_for_agent(force=force_refresh)
            capabilities = getattr(self.agent, "capabilities", None) or []
            topics = None
            if self.agent_descriptor is not None:
                topics = self.agent_descriptor.topics
            return self.task_manager.list_pending_tasks_for_agent(
                self.agent.id,
                pool_ids=pool_ids,
                capabilities=capabilities,
                topics=topics,
                sort_by_priority=True,
                refresh_from_store=refresh,
            )
        return self.task_manager.list_pending_tasks(refresh_from_store=refresh)

    async def _run_loop(self) -> None:
        """The main execution loop."""
        from .executor import StandardExecutor

        network = self.network if self.network is not None else AgentNetwork(self.transport)

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
                    coordination_metrics=self.coordination_metrics,
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
                    coordination_metrics=self.coordination_metrics,
                    **self.executor_kwargs,
                )
        else:
            executor = None

        while self.running:
            # 1. Wait for work (Event driven)
            # Wake up at least every few seconds for health checks or task polling if tasks aren't event-driven yet
            # (Tasks usually come from messages or internal generation)
            await self.scheduler.wait_for_work(timeout=self.scheduler_timeout_sec)

            if not self.running:
                break

            # 2. Poll inbox
            messages = self.inbox.poll()

            # 3. Poll task queue (scoped by pool/capabilities when pool_manager is set)
            tasks = self._get_visible_tasks()

            # 4. Decide (with optional ReAct tool loop)
            if messages or tasks:
                self.agent.on_tick(messages, tasks)
                tool_observations: list[dict[str, Any]] = []
                decisions: list[Any] = []
                for _ in range(max(0, self.max_tool_loop_iterations)):
                    with trace("agent.decide"):
                        decide_kwargs: dict[str, Any] = {}
                        if tool_observations:
                            decide_kwargs["tool_observations"] = tool_observations
                        adecide = getattr(self.agent, "adecide", None)
                        if adecide is not None and inspect.iscoroutinefunction(adecide):
                            decisions = cast(list[Any], await adecide(messages, tasks, **decide_kwargs))
                        elif inspect.iscoroutinefunction(self.agent.decide):
                            decisions = cast(list[Any], await self.agent.decide(messages, tasks, **decide_kwargs))
                        else:
                            decisions = cast(
                                list[Any],
                                await asyncio.to_thread(self.agent.decide, messages, tasks, **decide_kwargs),
                            )

                    from converge.core.decisions import Decision, InvokeTool
                    invoke_only = [d for d in decisions if isinstance(d, InvokeTool)]
                    other_decisions = [d for d in decisions if not isinstance(d, InvokeTool)]

                    if other_decisions and executor:
                        with trace("executor.execute"):
                            await executor.execute(other_decisions)
                        from converge.core.decisions import CreatePool, JoinPool, LeavePool

                        if any(isinstance(d, (JoinPool, LeavePool, CreatePool)) for d in other_decisions):
                            self._invalidate_pool_cache()
                    elif other_decisions:
                        for decision in other_decisions:
                            await self._execute_decision_fallback(decision)

                    if not invoke_only:
                        break
                    if not self.tool_registry or self.max_tool_loop_iterations <= 0:
                        if invoke_only and executor:
                            await executor.execute(cast(list[Decision], invoke_only))
                        break

                    for inv in invoke_only:
                        tool = self.tool_registry.get(inv.tool_name)
                        obs = {"tool_name": inv.tool_name, "params": inv.params}
                        if tool is not None:
                            try:
                                result = await asyncio.to_thread(tool.run, inv.params)
                                obs["result"] = result
                            except Exception as e:
                                obs["error"] = str(e)
                        else:
                            obs["error"] = "tool not found"
                        tool_observations.append(obs)

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

            # Optional release of expired task claims (claim_ttl_sec)
            if (
                self.claim_ttl_interval_sec is not None
                and self.task_manager is not None
            ):
                now = time.monotonic()
                if now - self._last_claim_ttl_ts >= self.claim_ttl_interval_sec:
                    released = self.task_manager.release_expired_claims(now)
                    self._last_claim_ttl_ts = now
                    if released:
                        logger.debug(
                            "Released %s expired claim(s): %s",
                            len(released),
                            released,
                        )

    async def _execute_decision_fallback(self, decision: Any) -> None:
        # Legacy fallback if no executor configured
        if hasattr(decision, 'sender'): # Message
            for hook in self.runtime_hooks:
                callback = getattr(hook, "on_fallback_pre_send", None)
                if not callable(callback):
                    continue
                try:
                    decision = callback(decision)
                except Exception:
                    logger.debug("runtime hook on_fallback_pre_send failed", exc_info=True)
                    decision = None
                if decision is None:
                    return
            if not decision.signature:
                decision = self.agent.sign_message(decision)
            await self.transport.send(decision)
