from abc import ABC, abstractmethod


class AdmissionPolicy(ABC):
    """
    Abstract base class for defining rules on how agents are admitted to a pool.
    """
    @abstractmethod
    def can_admit(self, agent_id: str, pool_context: dict) -> bool:
        """
        Determine if an agent is authorized to join.

        Args:
            agent_id (str): The unique fingerprint of the agent requesting admission.
            pool_context (dict): Arbitrary metadata about the pool or request (e.g., existing members, tokens).

        Returns:
            bool: True if the agent is admitted, False otherwise.
        """
        pass

class OpenAdmission(AdmissionPolicy):
    """
    A permissive policy that allows any agent to join.
    """
    def can_admit(self, agent_id: str, pool_context: dict) -> bool:
        """
        Check admission. Always returns True.

        Args:
            agent_id (str): Agent fingerprint.
            pool_context (dict): Pool context.

        Returns:
            bool: True.
        """
        return True

class WhitelistAdmission(AdmissionPolicy):
    """
    A restrictive policy that only allows agents present in a predefined whitelist.
    """
    def __init__(self, whitelist: list[str]):
        """
        Initialize the whitelist policy.

        Args:
            whitelist (List[str]): A list of authorized agent IDs.
        """
        self.whitelist = set(whitelist)

    def can_admit(self, agent_id: str, pool_context: dict) -> bool:
        """
        Check if the agent is in the whitelist.

        Args:
             agent_id (str): Agent fingerprint.
             pool_context (dict): Pool context.

        Returns:
             bool: True if whitelisted, False otherwise.
        """
        return agent_id in self.whitelist

class TokenAdmission(AdmissionPolicy):
    """
    A policy requiring a specific secret token to be present in the request context.
    """
    def __init__(self, required_token: str):
        """
        Initialize with the required token.

        Args:
            required_token (str): The secret token that must be provided.
        """
        self.required_token = required_token

    def can_admit(self, agent_id: str, pool_context: dict) -> bool:
        """
        Check if the correct token is provided in the pool context.

        Args:
             agent_id (str): Agent fingerprint.
             pool_context (dict): Context containing the 'token' key.

        Returns:
             bool: True if token matches, False otherwise.
        """
        # Check if the join request includes the token.
        # Note: pool_context here is assumed to contain request metadata for now.
        return pool_context.get("token") == self.required_token
