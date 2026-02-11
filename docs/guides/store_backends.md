# Implementing Store for external backends

The Store interface (`put`, `get`, `delete`, `list(prefix)`, and optional `put_if_absent`) can be implemented over any key-value backend. This guide outlines patterns for Redis, SQLite, or a database.

## Interface contract

- **put(key, value)**: Store or overwrite. Value must be serializable (e.g. pickle, JSON, or your format).
- **get(key)**: Return the value or None if absent.
- **delete(key)**: Remove the key; no-op if absent.
- **list(prefix)**: Return keys that start with `prefix` (e.g. `"task:"` for all task keys).
- **put_if_absent(key, value)**: Store only if key is absent; return True if stored, False if key existed. Override for atomicity (e.g. Redis SETNX, SQLite INSERT OR IGNORE).

## Redis

Use a single key per entry; keys can include colons (e.g. `task:uuid`). Serialize values with pickle, msgpack, or JSON. `list(prefix)` maps to `KEYS prefix*` or `SCAN` (prefer SCAN in production). `put_if_absent` can use `SET key value NX` for atomicity.

## SQLite

Single table: `(key TEXT PRIMARY KEY, value BLOB)`. Serialize values to bytes (pickle or msgpack). `list(prefix)` is `SELECT key FROM store WHERE key LIKE prefix||'%'`. `put_if_absent` can use `INSERT OR IGNORE` or a conditional insert.

## Database (e.g. PostgreSQL)

Same pattern as SQLite: key-value table, optional version column for optimistic concurrency. `put_if_absent` can use `INSERT ... ON CONFLICT (key) DO NOTHING` and check row count.

## Serialization

PoolManager, TaskManager, and DiscoveryService store Task, Pool, and AgentDescriptor objects. Ensure your serializer handles these types (pickle does; for JSON you would need a custom encoder or store dicts only). Schema or type changes may require a migration or version field.
