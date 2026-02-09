from dataclasses import dataclass
from enum import Enum
from typing import Any

from .identity import Identity


class AgentState(Enum):
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"

@dataclass
class Agent:
    """
    Autonomous computational entity that interacts with the network and executes decisions.

    Attributes:
        identity (Identity): Cryptographic identity of the agent.
        id (str): Unique fingerprint of the agent identity.
        capabilities (List[str]): List of capabilities this agent possesses.
        topics (List[Any]): List of topics this agent is interested in or manages.
        state (AgentState): Current operational state of the agent.
        pool_manager (Optional[Any]): Reference to the pool manager implementation.
        task_manager (Optional[Any]): Reference to the task manager implementation.
    """
    def __init__(self, identity: Identity):
        """
        Initialize a new Agent instance.

        Args:
            identity (Identity): The cryptographic identity for this agent.
        """
        self.identity = identity
        # The 'id' property already returns identity.fingerprint
        self.capabilities: list[str] = []
        self.topics: list[Any] = []
        self.pool_manager = None
        self.task_manager = None
        self.state = AgentState.IDLE

    @property
    def id(self) -> str:
        """
        Get the unique agent identifier (fingerprint).

        Returns:
            str: The agent's identity fingerprint.
        """
        return self.identity.fingerprint

    def decide(self, messages: list[Any], tasks: list[Any]) -> list[Any]:
        """
        The core decision loop for the agent.

        This method processes incoming messages and task updates to produce a list of
        decisions (actions) to be executed by the runtime.

        Args:
            messages (list[Any]): Validated messages from the inbox.
            tasks (list[Any]): Task updates or assignment requests.

        Returns:
            list[Any]: A list of Decision objects or Messages to send.
        """
        return []

    def on_start(self) -> None:
        """Called when the agent runtime starts. Override for setup logic."""
        pass

    def on_stop(self) -> None:
        """Called when the agent runtime stops. Override for cleanup logic."""
        pass

    def on_tick(self, messages: list[Any], tasks: list[Any]) -> None:
        """Called each loop iteration before decide. Override for per-tick logic."""
        pass

    def sign_message(self, message: Any) -> Any:
        # Avoid circular import by accepting Any and duck-typing or local import
        # In a real static typed world we'd move Message or interfaces to a common place
        return message.sign(self.identity)
