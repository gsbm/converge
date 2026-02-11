from abc import ABC, abstractmethod
from typing import Any


class Store(ABC):
    """
    Abstract base class for persistence.

    Optional **put_if_absent**: Override for atomic put-when-absent; default implementation
    is not atomic (get then put). Backends that need safe concurrency should override.
    """

    @abstractmethod
    def put(self, key: str, value: Any) -> None:
        """Store a value."""
        pass

    @abstractmethod
    def get(self, key: str) -> Any | None:
        """Retrieve a value."""
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete a value."""
        pass

    @abstractmethod
    def list(self, prefix: str = "") -> list[str]:
        """List keys starting with prefix."""
        pass

    def put_if_absent(self, key: str, value: Any) -> bool:
        """
        Store value only if key is absent. Return True if stored, False if key existed.
        Default implementation is not atomic; backends should override for atomicity.
        """
        if self.get(key) is not None:
            return False
        self.put(key, value)
        return True
