from typing import Any

from converge.core.pool import Pool
from converge.core.store import Store


class PoolManager:
    """
    Manages the lifecycle of agent pools and membership.

    Persists pool state to a backing store if provided. Handles creation,
    membership management (join/leave), and retrieval of pool data.
    """
    def __init__(self, store: Store | None = None):
        if store is None:
            from converge.extensions.storage.memory import MemoryStore
            store = MemoryStore()
        self.store = store
        self.pools: dict[str, Pool] = {}

    def create_pool(self, spec: dict[str, Any]) -> Pool:
        """
        Create a new pool based on a specification.

        Args:
            spec (Dict[str, Any]): Dictionary of arguments for the Pool constructor.
                May include "admission_policy": AdmissionPolicy instance.

        Returns:
            Pool: The newly created Pool instance.
        """
        spec = dict(spec)
        admission_policy_instance = spec.pop("admission_policy", None)
        if admission_policy_instance is not None and hasattr(
            admission_policy_instance, "can_admit",
        ):
            pass
        else:
            admission_policy_instance = None
        pool = Pool(**spec, admission_policy_instance=admission_policy_instance)
        self.pools[pool.id] = pool
        self.store.put(f"pool:{pool.id}", pool)
        return pool

    def join_pool(self, agent_id: str, pool_id: str) -> bool:
        """
        Add an agent to a pool.

        Args:
            agent_id (str): The fingerprint of the agent joining the pool.
            pool_id (str): The ID of the pool to join.

        Returns:
            bool: True if the agent successfully joined, False if pool not found.
        """
        pool = self.pools.get(pool_id)
        if not pool:
            # Try load
            pool = self.store.get(f"pool:{pool_id}")
            if pool:
                 self.pools[pool_id] = pool
            else:
                 return False

        policy = getattr(pool, "admission_policy_instance", None)
        if policy is not None and hasattr(policy, "can_admit"):
            pool_context = {
                "pool_id": pool.id,
                "existing_agents": list(pool.agents),
                "topics": [str(t) for t in pool.topics],
            }
            if not policy.can_admit(agent_id, pool_context):
                return False

        trust_model = getattr(pool, "trust_model", None)
        trust_threshold = getattr(pool, "trust_threshold", 0.0)
        if (
            trust_model is not None
            and hasattr(trust_model, "get_trust")
            and trust_model.get_trust(agent_id) < trust_threshold
        ):
            return False

        pool.add_agent(agent_id)
        self.store.put(f"pool:{pool.id}", pool)
        return True

    def leave_pool(self, agent_id: str, pool_id: str) -> None:
        """
        Remove an agent from a pool.

        Args:
            agent_id (str): The fingerprint of the agent leaving the pool.
            pool_id (str): The ID of the pool to leave.
        """
        pool = self.pools.get(pool_id)
        if not pool:
             pool = self.store.get(f"pool:{pool_id}")
             if pool:
                 self.pools[pool_id] = pool

        if pool:
            pool.remove_agent(agent_id)
            self.store.put(f"pool:{pool.id}", pool)

    def get_pool(self, pool_id: str) -> Pool | None:
        """
        Retrieve a pool by its ID.

        Args:
            pool_id (str): The ID of the pool to retrieve.

        Returns:
            Optional[Pool]: The Pool instance, or None if not found.
        """
        pool = self.pools.get(pool_id)
        if not pool:
            pool = self.store.get(f"pool:{pool_id}")
            if pool:
                self.pools[pool_id] = pool
        return pool

    def get_pools_for_agent(self, agent_id: str) -> list[str]:
        """
        Return the list of pool IDs that the agent is a member of.

        Args:
            agent_id (str): The fingerprint of the agent.

        Returns:
            List[str]: Pool IDs the agent has joined.
        """
        result: list[str] = []
        for pid, pool in self.pools.items():
            if agent_id in pool.agents:
                result.append(pid)
        for key in self.store.list("pool:"):
            pid = key.removeprefix("pool:") if key.startswith("pool:") else key
            if pid in self.pools:
                continue
            pool = self.store.get(key)
            if pool is not None and agent_id in getattr(pool, "agents", set()):
                result.append(pid)
        return result
