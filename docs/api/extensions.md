# converge.extensions

Optional extensions: storage, crypto, LLM. **Storage**: MemoryStore (in-memory) and FileStore (file-backed with pickle) implement the Store interface. **Crypto**: encrypt/decrypt (AES-256-GCM), derive_key (PBKDF2-HMAC-SHA256), secure_random_bytes. **LLM**: LLMAgent and providers (OpenAI, Anthropic, Mistral) for LLM-driven decide(); install with `pip install "converge[llm]"`.

```{eval-rst}
.. automodule:: converge.extensions.storage.memory
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: converge.extensions.storage.file
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: converge.extensions.crypto
   :members:
   :undoc-members:

.. automodule:: converge.extensions.llm
   :members:
   :undoc-members:
```
