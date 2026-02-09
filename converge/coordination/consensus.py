from collections import Counter
from typing import Any


class Consensus:
    """
    Basic consensus mechanisms for decision making.
    """

    @staticmethod
    def majority_vote(votes: list[Any]) -> Any:
        """
        Determine the winner by strict majority (> 50%).

        Args:
            votes (List[Any]): A list of votes (any hashable type).

        Returns:
            Any: The winning option, or None if no majority exists.
        """
        if not votes:
            return None

        count = Counter(votes)
        top, freq = count.most_common(1)[0]

        if freq > len(votes) / 2:
            return top
        return None

    @staticmethod
    def plurality_vote(votes: list[Any]) -> Any:
        """
        Determine the winner by plurality (most votes).

        Args:
            votes (List[Any]): A list of votes.

        Returns:
            Any: The winning option, or None if there is a tie for first place.
        """
        if not votes:
            return None

        count = Counter(votes)
        most_common = count.most_common(2)

        if not most_common:
            return None

        if len(most_common) == 1:
            return most_common[0][0]

        best, runner_up = most_common
        if best[1] == runner_up[1]:
            return None # Tie

        return best[0]
