"""
VersionedStore wrapper: reserved key __meta__:schema_version, get_version/set_version/check_version,
and optional on_version_change callback for migrations. Works with any Store.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from converge.core.store import Store

SCHEMA_VERSION_KEY = "__meta__:schema_version"


class VersionedStore(Store):
    """
    Wraps any Store and adds a schema version stored at a reserved key
    (__meta__:schema_version). Use get_version/set_version to read/write it,
    and check_version() to detect changes and invoke on_version_change(old, new)
    once per version change.
    """

    def __init__(
        self,
        store: Store,
        *,
        on_version_change: Callable[[Any, Any], None] | None = None,
    ) -> None:
        self._store = store
        self._on_version_change = on_version_change
        self._last_seen_version: Any = None

    def put(self, key: str, value: Any) -> None:
        self._store.put(key, value)

    def get(self, key: str) -> Any | None:
        return self._store.get(key)

    def delete(self, key: str) -> None:
        self._store.delete(key)

    def list(self, prefix: str = "") -> list[str]:
        return self._store.list(prefix)

    def put_if_absent(self, key: str, value: Any) -> bool:
        return self._store.put_if_absent(key, value)

    def get_version(self) -> Any:
        """Return the current schema version from the store, or None if unset."""
        return self._store.get(SCHEMA_VERSION_KEY)

    def set_version(self, version: Any) -> None:
        """Write the schema version to the store."""
        self._store.put(SCHEMA_VERSION_KEY, version)

    def check_version(self) -> Any:
        """
        Return the current stored version. If on_version_change is set and the
        stored version differs from the last seen version, call the callback
        with (old_version, new_version) and update the last seen version.
        """
        current = self.get_version()
        if self._on_version_change is not None and current != self._last_seen_version:
            self._on_version_change(self._last_seen_version, current)
            self._last_seen_version = current
        return current
