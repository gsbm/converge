"""Tests for converge.coordination.bidding."""

from converge.coordination.bidding import BiddingProtocol


def test_bidding_protocol():
    bp = BiddingProtocol()
    assert bp.active
    assert bp.bids == {}

    assert bp.submit_bid("agent1", 10.0, {})
    assert bp.submit_bid("agent2", 20.0, {})

    winner = bp.resolve()
    assert winner == "agent2"
    assert not bp.active

    assert not bp.submit_bid("agent3", 30.0, {})

    bp2 = BiddingProtocol()
    assert bp2.resolve() is None
