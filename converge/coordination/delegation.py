
class DelegationType:
    DIRECT = "direct"
    POOLED = "pooled"

class DelegationProtocol:
    """
    Manages the delegation of authority or tasks from one agent to another.
    """
    def __init__(self):
        self.delegations = {}

    def delegate(self, delegator_id: str, delegatee_id: str, scope: list[str]) -> str:
        """
        Create a new delegation mandate.

        Args:
            delegator_id (str): The agent granting authority.
            delegatee_id (str): The agent receiving authority.
            scope (List[str]): List of scopes/permissions being delegated (e.g. tokens, topics).

        Returns:
            str: A unique ID for the delegation record.
        """
        # Placeholder ID generation
        import uuid
        did = str(uuid.uuid4())
        self.delegations[did] = {
            "delegator": delegator_id,
            "delegatee": delegatee_id,
            "scope": scope,
            "active": True,
        }
        return did

    def revoke(self, delegation_id: str) -> bool:
        """
        Revoke an active delegation.

        Args:
            delegation_id (str): The ID of the delegation to revoke.

        Returns:
            bool: True if revoked, False if not found or already inactive.
        """
        if delegation_id in self.delegations:
            self.delegations[delegation_id]["active"] = False
            return True
        return False
