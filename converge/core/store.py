from abc import ABC, abstractmethod
from typing import Any


class Store(ABC):
    """
    Abstract base class for persistence.
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
