
class TrustModel:
    """
    Computes and manages trust scores for agents within the network.

    Trust is calculated based on historical interactions, direct feedback,
    and configured policies.
    """
    def __init__(self):
        self.scores: dict[str, float] = {}

    def update_trust(self, agent_id: str, score_delta: float) -> float:
        """
        Update the trust score for an agent.

        Args:
            agent_id (str): The agent ID.
            score_delta (float): The change in score (positive or negative).

        Returns:
            float: The new trust score.
        """
        current = self.scores.get(agent_id, 0.5) # Default neutral trust
        new_score = max(0.0, min(1.0, current + score_delta))
        self.scores[agent_id] = new_score
        return new_score

    def get_trust(self, agent_id: str) -> float:
        """
        Retrieve the current trust score for an agent.

        Args:
            agent_id (str): The agent ID.

        Returns:
            float: A score between 0.0 and 1.0.
        """
        return self.scores.get(agent_id, 0.5)
