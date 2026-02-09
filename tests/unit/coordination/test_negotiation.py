"""Tests for converge.coordination.negotiation."""


from converge.coordination.negotiation import NegotiationProtocol, NegotiationState


def test_negotiation_flow():
    proto = NegotiationProtocol()

    p1 = "price: 100"
    sid = proto.create_session("agentA", ["agentB"], p1)

    session = proto.get_session(sid)
    assert session.state == NegotiationState.PROPOSED
    assert session.current_proposal.content == p1

    p2 = "price: 90"
    proto.propose(sid, "agentB", p2)
    assert session.state == NegotiationState.COUNTERED
    assert session.current_proposal.content == p2

    proto.accept(sid, "agentA")
    assert session.state == NegotiationState.ACCEPTED


def test_negotiation_rejection():
    proto = NegotiationProtocol()
    sid = proto.create_session("agentA", ["agentB"], "deal")

    proto.reject(sid, "agentB")
    assert proto.get_session(sid).state == NegotiationState.REJECTED


def test_negotiation_branch_propose_non_participant():
    np = NegotiationProtocol()
    sid = np.create_session("initiator", ["p1"], "proposal")
    assert not np.propose(sid, "intruder", "stolen counter")


def test_negotiation_edge_cases():
    proto = NegotiationProtocol()
    sid = proto.create_session("agentA", ["agentB"], "deal")

    assert not proto.reject("missing_sid", "agentA")
    assert not proto.reject(sid, "agentC")
    assert not proto.accept(sid, "agentC")
    assert not proto.accept("missing_sid", "agentA")

    proto.accept(sid, "agentB")
    assert not proto.propose(sid, "agentA", "counter")
