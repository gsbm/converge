"""Tests for converge.core.agent."""

from converge.core.agent import Agent
from converge.core.identity import Identity
from converge.core.message import Message


def test_agent_decide_default():
    identity = Identity.generate()
    agent = Agent(identity)
    assert agent.decide([], []) == []
    msg = Message(sender=identity.fingerprint)
    signed = agent.sign_message(msg)
    assert signed.signature != b""
