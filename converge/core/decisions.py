from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .task import Task

if TYPE_CHECKING:
    from .message import Message

@dataclass
class Decision:
    """Base class for agent decisions."""
    pass

@dataclass
class SendMessage(Decision):
    """Decision to send a single message. Carries the Message to send."""
    message: "Message"

@dataclass
class JoinPool(Decision):
    pool_id: str

@dataclass
class LeavePool(Decision):
    pool_id: str

@dataclass
class CreatePool(Decision):
    spec: dict[str, Any]

@dataclass
class SubmitTask(Decision):
    task: Task

@dataclass
class ClaimTask(Decision):
    task_id: str

@dataclass
class ReportTask(Decision):
    task_id: str
    result: Any


@dataclass
class SubmitBid(Decision):
    """Submit a bid to an auction. Executor calls BiddingProtocol.submit_bid."""
    auction_id: str
    amount: float
    content: Any = None


@dataclass
class Vote(Decision):
    """Record a vote for a vote_id. Executor records (agent_id, option) for later resolution."""
    vote_id: str
    option: Any


@dataclass
class Propose(Decision):
    """Make or counter a proposal in a negotiation session. Executor calls NegotiationProtocol.propose."""
    session_id: str
    proposal_content: Any


@dataclass
class AcceptProposal(Decision):
    """Accept the current proposal in a session. Executor calls NegotiationProtocol.accept."""
    session_id: str


@dataclass
class RejectProposal(Decision):
    """Reject the current proposal. Executor calls NegotiationProtocol.reject."""
    session_id: str


@dataclass
class Delegate(Decision):
    """Create a delegation to another agent. Executor calls DelegationProtocol.delegate."""
    delegatee_id: str
    scope: list[str]


@dataclass
class RevokeDelegation(Decision):
    """Revoke a delegation. Executor calls DelegationProtocol.revoke."""
    delegation_id: str


@dataclass
class InvokeTool(Decision):
    """Invoke a registered tool by name with the given parameters. Executor runs the tool and may attach the result to a message or ReportTask."""
    tool_name: str
    params: dict[str, Any]
