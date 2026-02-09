import asyncio
import contextlib
import inspect
import logging
from typing import TYPE_CHECKING, Any, cast

from converge.core.agent import Agent
from converge.network.transport.base import Transport
from converge.observability.tracing import trace

if TYPE_CHECKING:
    from converge.observability.metrics import MetricsCollector


class Inbox:
    """
    Buffers incoming messages for the agent.
    Supports bounded queue with configurable behavior when full.
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
    ):
        self.agent = agent
        self.transport = transport
        self.inbox = Inbox()
        self.running = False
        self._loop_task: asyncio.Task | None = None
        self._listen_task: asyncio.Task | None = None
        self.metrics_collector = metrics_collector

        # New components
        from .executor import StandardExecutor
        from .scheduler import Scheduler
        self.pool_manager = pool_manager
        self.task_manager = task_manager
        self.scheduler = Scheduler()

        if pool_manager and task_manager:
            self.executor = StandardExecutor(
                agent.id, None, task_manager, pool_manager,
                metrics_collector=metrics_collector,
            )
            # Wait, StandardExecutor needs Network/Transport.
            # The original code acted on Transport directly for messages.
            # Let's adjust StandardExecutor or wrap Transport.
            # Actually, `AgentNetwork` wraps transport.
            # If we don't have AgentNetwork instance here, we can't use StandardExecutor easily without hacking.
            # To avoid breaking changes, let's keep inline execution or specific logic for now
            # OR wrap transport in a simple adapter if we really want to use Executor.
            # Let's simple-inline the Executor usage logic but modifying it to accept Transport.
            pass

    async def start(self) -> None:
        """Start the agent loop."""
        if self.running:
            return

        self.running = True

        self.agent.on_start()

        await self.transport.start()

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

        self.agent.on_stop()

        self._loop_task = None
        self._listen_task = None

    async def _listen_transport(self) -> None:
        """Continuously receive messages from transport and push to inbox."""
        while self.running:
            try:
                message = await self.transport.receive()
                if self.metrics_collector:
                    self.metrics_collector.inc("messages_received")
                await self.inbox.push(message)
                self.scheduler.notify()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.getLogger(__name__).warning("Error receiving message: %s", e)
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
            executor = StandardExecutor(
                self.agent.id, network, self.task_manager, self.pool_manager,
                metrics_collector=self.metrics_collector,
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

            # 3. Poll task queue
            tasks: list[Any] = []
            if self.task_manager is not None:
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

    async def _execute_decision_fallback(self, decision: Any) -> None:
        # Legacy fallback if no executor configured
        if hasattr(decision, 'sender'): # Message
             if not decision.signature:
                 decision = self.agent.sign_message(decision)
             await self.transport.send(decision)
