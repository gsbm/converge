# Extensions

Optional extensions add crypto utilities, LLM-driven agents, and additional storage backends. The core package does not depend on them; install the relevant extras or use the modules only when the dependencies are present.

## Crypto

The crypto extension provides symmetric encryption, key derivation, and secure random bytes. It uses the existing `cryptography` dependency; no extra install is required.

**Module:** `converge.extensions.crypto`

- **`encrypt(plaintext, key, associated_data=None)`**: AES-256-GCM encryption; key must be 32 bytes. Returns ciphertext (bytes).
- **`decrypt(ciphertext, key, associated_data=None)`**: Decryption; raises on invalid key or tampering.
- **`derive_key(password, salt, length=32, iterations=100_000)`**: PBKDF2-HMAC-SHA256 key derivation; password is str, salt is bytes.
- **`secure_random_bytes(length)`**: Cryptographically secure random bytes.

Use cases: encrypting message payloads at rest, deriving keys from secrets, generating nonces and ids.

Example:

```python
from converge.extensions.crypto import encrypt, decrypt, derive_key, secure_random_bytes

key = secure_random_bytes(32)
ciphertext = encrypt(b"secret data", key)
plaintext = decrypt(ciphertext, key)

salt = secure_random_bytes(16)
key2 = derive_key("password", salt, length=32)
```

## LLM

The LLM extension provides an **LLMAgent** that uses an LLM to produce decisions in `decide()`. Supported providers: OpenAI, Anthropic, Mistral AI. Install all provider dependencies with:

```bash
pip install "converge[llm]"
```

**Module:** `converge.extensions.llm`

- **`LLMAgent(identity, provider, system_prompt=None)`**: Agent that calls `provider.chat(messages)` and parses the response as a JSON array of decisions.
- **`OpenAIProvider(api_key=None, model="gpt-4o-mini")`**: OpenAI API (uses `OPENAI_API_KEY` if api_key is None).
- **`AnthropicProvider(api_key=None, model="claude-sonnet-4-20250514")`**: Anthropic API.
- **`MistralProvider(api_key=None, model="mistral-small-latest")`**: Mistral AI API.

The provider must implement `chat(messages: list[dict], **kwargs) -> str`. The LLM is expected to return a JSON array of decision objects. Supported decision types in the prompt: `SendMessage`, `JoinPool`, `LeavePool`, `ClaimTask`, `SubmitTask`. Message format: `{"type": "SendMessage", "message": {"sender": "<id>", "topics": [], "payload": {...}}}`. Task format for SubmitTask: `{"id": "<id>", "objective": {...}, "inputs": {...}}`.

Example:

```python
from converge.core.identity import Identity
from converge.extensions.llm import LLMAgent, OpenAIProvider

identity = Identity.generate()
provider = OpenAIProvider(api_key="sk-...", model="gpt-4o-mini")
agent = LLMAgent(identity, provider=provider)
# Use with AgentRuntime like any Agent
```

Custom system prompts can be passed as `system_prompt=...`. The agent formats incoming messages and tasks into a prompt and parses the model output into `converge.core.decisions` objects.

## Storage

**MemoryStore**: In-memory key-value store; implements `converge.core.store.Store`. No extra dependency.

**FileStore**: File-backed store using pickle; directory per store, one file per key. No extra dependency.

**Modules**: `converge.extensions.storage.memory`, `converge.extensions.storage.file`

Used by pool manager, task manager, and discovery service when a store is provided. See [API/extensions](../api/extensions.md).

## WebSocket transport

A **WebSocket transport** implementation may be present under `converge.network.transport.websocket`. Its dependency is installed with:

```bash
pip install "converge[websocket]"
```

See the API reference and source for the exact interface and usage.
