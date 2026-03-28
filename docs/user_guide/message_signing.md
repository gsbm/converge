# Message signing compatibility

Converge signs messages with Ed25519 over a deterministic msgpack payload.

## Canonical signing contract

`Message._serialize_for_signing()` signs this structure:

- `id`
- `sender`
- `recipient`
- `topics` as string list
- `payload` with canonical map ordering (sorted keys recursively)
- `task_id`
- `timestamp`

Serialization uses msgpack with `use_bin_type=True`.

## Why this matters

- **Cross-version verification:** If signing bytes change, old/new agents may reject each other.
- **Cross-language compatibility:** Non-Python clients can verify signatures if they follow the same canonical payload shape and ordering.

## Compatibility vector

Reference vector covered by unit tests:

- private key: `1f` repeated 32 bytes
- message id: `msg-fixed-001`
- timestamp: `1700000000000`
- payload: `{"b": 2, "a": {"z": 1, "y": 2}}`
- expected signature (hex):

`c68853863eac5d9371772d11d12d4356bb341d97934858e4667d76b3dc8f71695c44cb20a55a757bad792d36885ee41f67391c9e733fd0d498de788126f37e08`

If this vector changes, treat it as a compatibility break and document migration behavior.
