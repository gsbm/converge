"""Tests for converge.coordination.consensus."""

from collections import Counter
from unittest.mock import patch

from converge.coordination.consensus import Consensus


def test_consensus_majority():
    votes = ["A", "A", "B"]
    assert Consensus.majority_vote(votes) == "A"

    votes_tie = ["A", "B"]
    assert Consensus.majority_vote(votes_tie) is None

    votes_split = ["A", "B", "C"]
    assert Consensus.majority_vote(votes_split) is None


def test_consensus_plurality():
    votes = ["A", "B", "C", "A"]
    assert Consensus.majority_vote(votes) is None
    assert Consensus.plurality_vote(votes) == "A"

    votes_tie = ["A", "A", "B", "B"]
    assert Consensus.plurality_vote(votes_tie) is None

    assert Consensus.plurality_vote(["A"]) == "A"
    assert Consensus.majority_vote([]) is None
    assert Consensus.plurality_vote([]) is None


def test_consensus_plurality_empty_most_common():
    with patch.object(Counter, "most_common", return_value=[]):
        assert Consensus.plurality_vote(["A", "B"]) is None
