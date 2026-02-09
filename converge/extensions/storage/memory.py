from typing import Any

from converge.core.store import Store


class MemoryStore(Store):
    """
    In-memory storage implementation.
    """
    def __init__(self):
        self._data: dict[str, Any] = {}

    def put(self, key: str, value: Any) -> None:
        self._data[key] = value

    def get(self, key: str) -> Any | None:
        return self._data.get(key)

    def delete(self, key: str) -> None:
        if key in self._data:
            del self._data[key]

    def list(self, prefix: str = "") -> list[str]:
        return [k for k in self._data if k.startswith(prefix)]
