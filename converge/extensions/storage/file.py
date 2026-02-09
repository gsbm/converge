import pickle
from pathlib import Path
from typing import Any

from converge.core.store import Store


class FileStore(Store):
    """
    File-based storage implementation using pickle for simplicity with objects.
    In production, might want JSON for portability, but pickle handles custom classes easier for now.
    """
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_path(self, key: str) -> Path:
        # Sanitize key to be safe filename?
        # For now assume simple keys
        return self.base_path / key

    def put(self, key: str, value: Any) -> None:
        path = self._get_path(key)
        with path.open("wb") as f:
            pickle.dump(value, f)

    def get(self, key: str) -> Any | None:
        path = self._get_path(key)
        if not path.exists():
            return None
        try:
            with path.open("rb") as f:
                return pickle.load(f)
        except Exception:
            return None

    def delete(self, key: str) -> None:
        path = self._get_path(key)
        if path.exists():
            path.unlink()

    def list(self, prefix: str = "") -> list[str]:
        # This is a bit tricky if keys match filenames exactly
        if not self.base_path.exists():
            return []
        return [f.name for f in self.base_path.iterdir() if f.name.startswith(prefix)]
