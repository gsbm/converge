import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NegotiationState(Enum):
    PROPOSED = "proposed"
    COUNTERED = "countered"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CLOSED = "closed"

@dataclass
class Proposal:
    """
    A proposal within a negotiation session.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    proposer_id: str = ""
    content: Any = None
    timestamp: float = 0.0

@dataclass
class NegotiationSession:
    """
    Tracks the state of a negotiation between agents.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    participants: list[str] = field(default_factory=list)
    history: list[Proposal] = field(default_factory=list)
    state: NegotiationState = NegotiationState.PROPOSED
    current_proposal: Proposal | None = None

class NegotiationProtocol:
    """
    Manages negotiation sessions and state transitions.
    """
    def __init__(self):
        self.sessions: dict[str, NegotiationSession] = {}

    def create_session(self, initiator_id: str, participants: list[str], initial_proposal: Any) -> str:
        """
        Start a new negotiation session.

        Args:
            initiator_id (str): Fingerprint of the agent starting the session.
            participants (List[str]): List of other agents invited to negotiate.
            initial_proposal (Any): The initial content/offer.

        Returns:
            str: The unique ID of the new session.
        """
        session = NegotiationSession(participants=[initiator_id] + participants)
        proposal = Proposal(proposer_id=initiator_id, content=initial_proposal)
        session.history.append(proposal)
        session.current_proposal = proposal
        session.state = NegotiationState.PROPOSED

        self.sessions[session.id] = session
        return session.id

    def propose(self, session_id: str, agent_id: str, content: Any) -> bool:
        """
        Make a new proposal (or counter-proposal) in an existing session.

        Args:
            session_id (str): The ID of the session.
            agent_id (str): The fingerprint of the agent making the proposal.
            content (Any): The content of the new proposal.

        Returns:
            bool: True if proposal was accepted into the session, False otherwise.
        """
        session = self.sessions.get(session_id)
        if not session or session.state in [NegotiationState.ACCEPTED, NegotiationState.REJECTED, NegotiationState.CLOSED]:
            return False

        if agent_id not in session.participants:
            return False

        proposal = Proposal(proposer_id=agent_id, content=content)
        session.history.append(proposal)
        session.current_proposal = proposal
        session.state = NegotiationState.COUNTERED
        return True

    def accept(self, session_id: str, agent_id: str) -> bool:
        """
        Accept the current proposal.

        Args:
            session_id (str): The ID of the session.
            agent_id (str): The fingerprint of the agent accepting.

        Returns:
            bool: True if acceptance was recorded, False otherwise.
        """
        session = self.sessions.get(session_id)
        if not session or not session.current_proposal:
            return False

        if agent_id not in session.participants:
            return False

        session.state = NegotiationState.ACCEPTED
        return True

    def reject(self, session_id: str, agent_id: str) -> bool:
        """
        Reject the current proposal and close session.

        Args:
             session_id (str): The ID of the session.
             agent_id (str): The fingerprint of the agent rejecting.

        Returns:
             bool: True if rejection was recorded, False otherwise.
        """
        session = self.sessions.get(session_id)
        if not session:
            return False

        if agent_id not in session.participants:
            return False

        session.state = NegotiationState.REJECTED
        return True

    def get_session(self, session_id: str) -> NegotiationSession | None:
        """
        Retrieve a session by ID.

        Args:
            session_id (str): The ID of the session.

        Returns:
            Optional[NegotiationSession]: The session object or None.
        """
        return self.sessions.get(session_id)
