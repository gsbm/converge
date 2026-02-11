import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, Protocol

from converge.coordination.pool_manager import PoolManager
from converge.coordination.task_manager import TaskManager

if TYPE_CHECKING:
    from converge.coordination.bidding import BiddingProtocol
    from converge.coordination.delegation import DelegationProtocol
    from converge.coordination.negotiation import NegotiationProtocol
    from converge.core.tools import ToolRegistry
    from converge.observability.metrics import MetricsCollector
    from converge.observability.replay import ReplayLog
    from converge.policy.safety import ActionPolicy, ResourceLimits
from converge.core.decisions import (
    AcceptProposal,
    ClaimTask,
    CreatePool,
    Decision,
    Delegate,
    InvokeTool,
    JoinPool,
    LeavePool,
    Propose,
    RejectProposal,
    ReportTask,
    RevokeDelegation,
    SendMessage,
    SubmitBid,
    SubmitTask,
    Vote,
)
from converge.network.network import AgentNetwork

logger = logging.getLogger(__name__)


class Executor(Protocol):
    """
    Protocol for action executors.
    """
    async def execute(self, decisions: list[Decision]) -> None:
        pass


class StandardExecutor:
    """
    Standard implementation of the Executor.
    Directly acts upon the Network and Managers; optionally runs coordination
    protocols (bidding, negotiation, delegation) and records votes.
    """

    def __init__(
        self,
        agent_id: str,
        network: AgentNetwork | None,
        task_manager: TaskManager,
        pool_manager: PoolManager,
        metrics_collector: "MetricsCollector | None" = None,
        bidding_protocols: "dict[str, BiddingProtocol] | None" = None,
        negotiation_protocol: "NegotiationProtocol | None" = None,
        delegation_protocol: "DelegationProtocol | None" = None,
        votes_store: dict[str, list[tuple[str, Any]]] | None = None,
        safety_policy: "tuple[ResourceLimits | None, ActionPolicy | None] | None" = None,
        replay_log: "ReplayLog | None" = None,
        tool_registry: "ToolRegistry | None" = None,
        custom_handlers: dict[type, Callable[[Decision], Awaitable[None]]] | None = None,
        tool_timeout_sec: float | None = None,
        tool_allowlist: set[str] | None = None,
    ):
        """
        Initialize the executor.

        Args:
            agent_id: The fingerprint of the agent executing decisions.
            network: Optional network for sending messages.
            task_manager: Task manager for task lifecycle.
            pool_manager: Pool manager for pool membership.
            metrics_collector: Optional metrics collector.
            bidding_protocols: Optional dict of auction_id -> BiddingProtocol for SubmitBid.
            negotiation_protocol: Optional protocol for Propose/AcceptProposal/RejectProposal.
            delegation_protocol: Optional protocol for Delegate/RevokeDelegation.
            votes_store: Optional dict vote_id -> list of (agent_id, option) for Vote.
            safety_policy: Optional (ResourceLimits, ActionPolicy). When set, ActionPolicy
                restricts which decision types are allowed; ResourceLimits validate
                SubmitTask/ClaimTask constraints (cpu, memory_mb).
            replay_log: Optional replay log. When set, SendMessage decisions record
                the sent message for audit and replay.
            tool_registry: Optional registry of tools. When set, InvokeTool decisions
                look up the tool by name and run it with the given params; result is
                discarded (agent may emit ReportTask separately to report results).
            custom_handlers: Optional dict mapping decision type -> async handler(decision).
                For custom Decision subclasses, register a handler so the executor runs it
                instead of logging "Unknown decision type".
            tool_timeout_sec: Optional timeout in seconds for tool execution. When set,
                tool.run(params) is run in a thread and must complete within this time
                or the call is cancelled and an error is logged; the agent may report
                task failure separately.
            tool_allowlist: Optional set of allowed tool names. When set, InvokeTool for
                a tool not in this set is skipped and a warning is logged.
        """
        self.agent_id = agent_id
        self.network = network
        self.task_manager = task_manager
        self.pool_manager = pool_manager
        self.metrics_collector = metrics_collector
        self.bidding_protocols = bidding_protocols or {}
        self.negotiation_protocol = negotiation_protocol
        self.delegation_protocol = delegation_protocol
        self.votes_store = votes_store
        self.safety_policy = safety_policy
        self.replay_log = replay_log
        self.tool_registry = tool_registry
        self.custom_handlers = custom_handlers or {}
        self.tool_timeout_sec = tool_timeout_sec
        self.tool_allowlist = tool_allowlist

    async def execute(self, decisions: list[Decision]) -> None:
        """
        Execute a batch of decisions.

        Args:
            decisions (List[Decision]): The decisions to execute.
        """
        for decision in decisions:
            try:
                if self.safety_policy is not None:
                    limits, action_policy = self.safety_policy
                    decision_type_name = type(decision).__name__
                    if action_policy is not None and not action_policy.is_allowed(decision_type_name):
                        logger.warning("Decision %s not allowed by ActionPolicy", decision_type_name)
                        continue
                    if limits is not None and isinstance(decision, (SubmitTask, ClaimTask)):
                        requested_cpu = 0.0
                        requested_mem = 0
                        if isinstance(decision, SubmitTask):
                            c = decision.task.constraints
                            requested_cpu = float(c.get("cpu", c.get("max_cpu_tokens", 0)))
                            requested_mem = int(c.get("memory_mb", c.get("max_memory_mb", 0)))
                        elif isinstance(decision, ClaimTask):
                            task = self.task_manager.get_task(decision.task_id)
                            if task is not None:
                                c = task.constraints
                                requested_cpu = float(c.get("cpu", c.get("max_cpu_tokens", 0)))
                                requested_mem = int(c.get("memory_mb", c.get("max_memory_mb", 0)))
                        from converge.policy.safety import validate_safety
                        if not validate_safety(limits, requested_cpu, requested_mem):
                            logger.warning(
                                "Task resource request exceeds limits: cpu=%s mem=%s",
                                requested_cpu, requested_mem,
                            )
                            continue

                if self.metrics_collector:
                    self.metrics_collector.inc("decisions_executed")
                if isinstance(decision, SendMessage):
                    if self.network is not None:
                        logger.debug(f"Executing SendMessage: {decision.message.id}")
                        await self.network.send(decision.message)
                        if self.replay_log is not None:
                            self.replay_log.record_message(decision.message)
                        if self.metrics_collector:
                            self.metrics_collector.inc("messages_sent")

                elif isinstance(decision, SubmitTask):
                    logger.debug(f"Executing SubmitTask: {decision.task.id}")
                    self.task_manager.submit(decision.task)

                elif isinstance(decision, ClaimTask):
                    logger.debug(f"Executing ClaimTask: {decision.task_id}")
                    success = self.task_manager.claim(self.agent_id, decision.task_id)
                    if not success:
                        logger.warning(f"Failed to claim task {decision.task_id}")

                elif isinstance(decision, JoinPool):
                    logger.debug(f"Executing JoinPool: {decision.pool_id}")
                    self.pool_manager.join_pool(self.agent_id, decision.pool_id)

                elif isinstance(decision, LeavePool):
                    logger.debug(f"Executing LeavePool: {decision.pool_id}")
                    self.pool_manager.leave_pool(self.agent_id, decision.pool_id)

                elif isinstance(decision, CreatePool):
                    logger.debug(f"Executing CreatePool: {decision.spec}")
                    self.pool_manager.create_pool(decision.spec)

                elif isinstance(decision, ReportTask):
                    logger.debug(f"Executing ReportTask: {decision.task_id}")
                    self.task_manager.report(self.agent_id, decision.task_id, decision.result)

                elif isinstance(decision, SubmitBid):
                    proto = self.bidding_protocols.get(decision.auction_id)
                    if proto is not None:
                        logger.debug(f"Executing SubmitBid: auction={decision.auction_id}")
                        proto.submit_bid(self.agent_id, decision.amount, decision.content)
                    else:
                        logger.warning(f"No BiddingProtocol for auction {decision.auction_id}")

                elif isinstance(decision, Vote):
                    if self.votes_store is not None:
                        logger.debug(f"Executing Vote: vote_id={decision.vote_id}")
                        self.votes_store.setdefault(decision.vote_id, []).append(
                            (self.agent_id, decision.option),
                        )
                    else:
                        logger.warning("Vote ignored: no votes_store configured")

                elif isinstance(decision, Propose):
                    if self.negotiation_protocol is not None:
                        logger.debug(f"Executing Propose: session={decision.session_id}")
                        self.negotiation_protocol.propose(
                            decision.session_id, self.agent_id, decision.proposal_content,
                        )
                    else:
                        logger.warning("Propose ignored: no negotiation_protocol")

                elif isinstance(decision, AcceptProposal):
                    if self.negotiation_protocol is not None:
                        logger.debug(f"Executing AcceptProposal: session={decision.session_id}")
                        self.negotiation_protocol.accept(decision.session_id, self.agent_id)
                    else:
                        logger.warning("AcceptProposal ignored: no negotiation_protocol")

                elif isinstance(decision, RejectProposal):
                    if self.negotiation_protocol is not None:
                        logger.debug(f"Executing RejectProposal: session={decision.session_id}")
                        self.negotiation_protocol.reject(decision.session_id, self.agent_id)
                    else:
                        logger.warning("RejectProposal ignored: no negotiation_protocol")

                elif isinstance(decision, Delegate):
                    if self.delegation_protocol is not None:
                        logger.debug(f"Executing Delegate: delegatee={decision.delegatee_id}")
                        self.delegation_protocol.delegate(
                            self.agent_id, decision.delegatee_id, decision.scope,
                        )
                    else:
                        logger.warning("Delegate ignored: no delegation_protocol")

                elif isinstance(decision, RevokeDelegation):
                    if self.delegation_protocol is not None:
                        logger.debug(f"Executing RevokeDelegation: {decision.delegation_id}")
                        self.delegation_protocol.revoke(decision.delegation_id)
                    else:
                        logger.warning("RevokeDelegation ignored: no delegation_protocol")

                elif isinstance(decision, InvokeTool):
                    if self.tool_registry is not None:
                        if self.tool_allowlist is not None and decision.tool_name not in self.tool_allowlist:
                            logger.warning(
                                "InvokeTool skipped: tool %s not in allowlist",
                                decision.tool_name,
                            )
                        else:
                            tool = self.tool_registry.get(decision.tool_name)
                            if tool is not None:
                                logger.debug(f"Executing InvokeTool: {decision.tool_name}")
                                try:
                                    if self.tool_timeout_sec is not None:
                                        await asyncio.wait_for(
                                            asyncio.to_thread(tool.run, decision.params),
                                            timeout=self.tool_timeout_sec,
                                        )
                                    else:
                                        tool.run(decision.params)
                                    if self.metrics_collector:
                                        self.metrics_collector.inc("tools_invoked")
                                except TimeoutError:
                                    logger.error(
                                        "Tool %s timed out after %.1fs",
                                        decision.tool_name,
                                        self.tool_timeout_sec,
                                    )
                                except Exception as e:
                                    logger.error(f"Tool {decision.tool_name} failed: {e}")
                            else:
                                logger.warning(f"Tool not found: {decision.tool_name}")
                    else:
                        logger.warning("InvokeTool ignored: no tool_registry configured")

                else:
                    handler = self.custom_handlers.get(type(decision))
                    if handler is not None:
                        await handler(decision)
                    else:
                        logger.warning(f"Unknown decision type: {type(decision)}")

            except Exception as e:
                logger.error(f"Error executing decision {decision}: {e}")
