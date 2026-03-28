# Implementing Store for external backends

The Store interface (`put`, `get`, `delete`, `list(prefix)`, and optional `put_if_absent`) can be implemented over any key-value backend. This guide outlines patterns for Redis, SQLite, or a database.

## Built-in Redis and SQLite backends

Converge provides **RedisStore** and **SQLiteStore** under `converge.extensions.storage` with atomic `put_if_absent`, suitable for multi-process deployments.

- **SQLiteStore** (`converge.extensions.storage.sqlite_store`): Single file path, stdlib only. `SQLiteStore(path: str | Path)`; table `(key TEXT PRIMARY KEY, value BLOB)`; pickle serialization; `list(prefix)` via `LIKE prefix%`; `put_if_absent` via `INSERT OR IGNORE`.
- **RedisStore** (`converge.extensions.storage.redis_store`): Requires source extra install `pip install -e ".[store-backends]"` (adds `redis>=5.0`). `RedisStore(redis_url="redis://localhost:6379/0", *, client=None)`; pickle serialization; `list(prefix)` via SCAN; `put_if_absent` via SET NX.

## VersionedStore and migration hook

A **VersionedStore** wrapper (`converge.extensions.storage.versioned`) adds a reserved metadata key `__meta__:schema_version` and optional migration callback. Use it with any Store:

- **get_version()** / **set_version(version)**: Read or write the schema version (e.g. integer or string).
- **check_version()**: Returns the current stored version; if you passed **on_version_change(old_version, new_version)** to the constructor, the callback is invoked once when the stored version differs from the last seen value (e.g. after an upgrade). Use this to run migrations or clear caches.

Example: wrap a store, set initial version, and register a callback for upgrades:

```python
from converge.extensions.storage.versioned import VersionedStore, SCHEMA_VERSION_KEY
from converge.extensions.storage.memory import MemoryStore

store = MemoryStore()
def on_change(old, new):
    print(f"Version changed from {old} to {new}")  # e.g. run migrations
versioned = VersionedStore(store, on_version_change=on_change)
versioned.set_version(1)
assert versioned.get_version() == 1
versioned.set_version(2)
versioned.check_version()  # calls on_change(1, 2)
```

## Interface contract

- **put(key, value)**: Store or overwrite. Value must be serializable (e.g. pickle, JSON, or your format).
- **get(key)**: Return the value or None if absent.
- **delete(key)**: Remove the key; no-op if absent.
- **list(prefix)**: Return keys that start with `prefix` (e.g. `"task:"` for all task keys).
- **put_if_absent(key, value)**: Store only if key is absent; return True if stored, False if key existed. Override for atomicity (e.g. Redis SETNX, SQLite INSERT OR IGNORE).
- **Capability flags**: Backends may expose `atomic_put_if_absent` and `supports_locking` booleans to describe operational guarantees to callers.

## Redis

Use a single key per entry; keys can include colons (e.g. `task:uuid`). Serialize values with pickle, msgpack, or JSON. `list(prefix)` maps to `KEYS prefix*` or `SCAN` (prefer SCAN in production). `put_if_absent` can use `SET key value NX` for atomicity.

## SQLite

Single table: `(key TEXT PRIMARY KEY, value BLOB)`. Serialize values to bytes (pickle or msgpack). `list(prefix)` is `SELECT key FROM store WHERE key LIKE prefix||'%'`. `put_if_absent` can use `INSERT OR IGNORE` or a conditional insert.

## Database (e.g. PostgreSQL)

Same pattern as SQLite: key-value table, optional version column for optimistic concurrency. `put_if_absent` can use `INSERT ... ON CONFLICT (key) DO NOTHING` and check row count.

## Serialization

PoolManager, TaskManager, and DiscoveryService store Task, Pool, and AgentDescriptor objects. Ensure your serializer handles these types (pickle does; for JSON you would need a custom encoder or store dicts only). Schema or type changes may require a migration or version field.
