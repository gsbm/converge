import logging
from typing import TYPE_CHECKING, Protocol

from converge.coordination.pool_manager import PoolManager
from converge.coordination.task_manager import TaskManager

if TYPE_CHECKING:
    from converge.observability.metrics import MetricsCollector
from converge.core.decisions import (
    ClaimTask,
    CreatePool,
    Decision,
    JoinPool,
    LeavePool,
    ReportTask,
    SendMessage,
    SubmitTask,
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
    Directly acts upon the Network and Managers.
    """
    def __init__(
        self,
        agent_id: str,
        network: AgentNetwork | None,
        task_manager: TaskManager,
        pool_manager: PoolManager,
        metrics_collector: "MetricsCollector | None" = None,
    ):
        self.agent_id = agent_id
        self.network = network
        self.task_manager = task_manager
        self.pool_manager = pool_manager
        self.metrics_collector = metrics_collector

    async def execute(self, decisions: list[Decision]) -> None:
        """
        Execute a batch of decisions.

        Args:
            decisions (List[Decision]): The decisions to execute.
        """
        for decision in decisions:
            try:
                if self.metrics_collector:
                    self.metrics_collector.inc("decisions_executed")
                if isinstance(decision, SendMessage):
                    if self.network is not None:
                        logger.debug(f"Executing SendMessage: {decision.message.id}")
                        await self.network.send(decision.message)
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

                else:
                    logger.warning(f"Unknown decision type: {type(decision)}")

            except Exception as e:
                logger.error(f"Error executing decision {decision}: {e}")
