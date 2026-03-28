import os
import pickle
import tempfile
from base64 import urlsafe_b64decode, urlsafe_b64encode
from pathlib import Path
from typing import Any

from converge.core.store import Store


class FileStore(Store):
    """
    File-based storage using pickle.

    Keys are encoded to safe filenames to avoid path traversal and accidental
    directory escaping. Writes are atomic via temp-file + replace.
    """

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _encode_key(key: str) -> str:
        encoded = urlsafe_b64encode(key.encode("utf-8")).decode("ascii")
        return encoded.rstrip("=") or "_"

    @staticmethod
    def _decode_name(name: str) -> str | None:
        if name == "_":
            return ""
        padding = "=" * ((4 - (len(name) % 4)) % 4)
        try:
            return urlsafe_b64decode((name + padding).encode("ascii")).decode("utf-8")
        except Exception:
            return None

    def _get_path(self, key: str) -> Path:
        return self.base_path / self._encode_key(key)

    def _get_legacy_path(self, key: str) -> Path:
        # Backward compatibility for older stores with raw key filenames.
        return self.base_path / key

    def put(self, key: str, value: Any) -> None:
        path = self._get_path(key)
        fd, tmp_name = tempfile.mkstemp(prefix=".tmp-", dir=str(self.base_path))
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "wb") as f:
                pickle.dump(value, f)
                f.flush()
            tmp_path.replace(path)
        finally:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

    def get(self, key: str) -> Any | None:
        path = self._get_path(key)
        legacy_path = self._get_legacy_path(key)
        target = path if path.exists() else legacy_path
        if not target.exists():
            return None
        try:
            with target.open("rb") as f:
                return pickle.load(f)
        except Exception:
            return None

    def delete(self, key: str) -> None:
        for path in (self._get_path(key), self._get_legacy_path(key)):
            if path.exists():
                path.unlink()

    def list(self, prefix: str = "") -> list[str]:
        if not self.base_path.exists():
            return []
        keys: list[str] = []
        seen: set[str] = set()
        for f in self.base_path.iterdir():
            decoded = self._decode_name(f.name)
            key = decoded if decoded is not None else f.name
            if key.startswith(prefix) and key not in seen:
                keys.append(key)
                seen.add(key)
        return keys

    def put_if_absent(self, key: str, value: Any) -> bool:
        path = self._get_path(key)
        if path.exists() or self._get_legacy_path(key).exists():
            return False
        try:
            with path.open("xb") as f:
                pickle.dump(value, f)
            return True
        except FileExistsError:
            return False
