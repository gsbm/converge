# Installation

## Requirements

- **Python:** 3.11 or newer.

## Base install

From PyPI:

```bash
pip install converge
```

From source (editable):

```bash
git clone https://github.com/your-org/converge.git
cd converge
pip install -e .
```

The base package includes: core (agent, identity, message, topic, task, pool, capability, store, decisions), network (discovery, identity registry, transports: base, local, TCP), coordination (pool manager, task manager, negotiation, consensus, bidding, delegation), runtime (loop, scheduler, executor), policy (admission, trust, governance, safety), observability (logging, tracing, metrics, replay), and in-memory storage. It does **not** include the CLI entrypoint, YAML config support, LLM providers, or WebSocket transport; use optional extras for those.

## Optional extras

| Extra | Purpose | Typical use |
|-------|---------|-------------|
| `converge[llm]` | OpenAI, Anthropic, and Mistral LLM providers; required for `LLMAgent` and provider classes. | LLM-driven agents. |
| `converge[websocket]` | WebSocket transport dependency (`websockets`). | WebSocket-based transport implementation. |
| `converge[cli]` | PyYAML for config file parsing. | Use `converge` CLI with YAML config. |
| `converge[docs]` | Sphinx, MyST, Shibuya theme. | Build documentation locally. |
| `converge[dev]` | pytest, coverage, ruff, pyright, pre-commit, pip-audit, and LLM providers. | Development and CI. |

Examples:

```bash
pip install "converge[llm]"        # All LLM providers
pip install "converge[cli]"        # CLI with YAML config
pip install -e ".[dev]"            # Development and tests
pip install -e ".[docs]"           # Build docs: cd docs && make html
```

## Development setup

1. Clone the repository and create a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

2. Install in editable mode with dev dependencies:

   ```bash
   pip install -e ".[dev]"
   ```

3. (Optional) Install pre-commit hooks:

   ```bash
   pre-commit install
   ```

4. Run tests:

   ```bash
   pytest -v
   ```

   For coverage (target 98%+):

   ```bash
   coverage run -m pytest tests/ --ignore=tests/unit/network/transport/test_tcp.py
   coverage report --fail-under=98
   ```

   TCP tests require network; run the full suite without the ignore for complete coverage where the environment allows.

## Building documentation

```bash
pip install -e ".[docs]"
cd docs && make html
```

Open `docs/_build/html/index.html` in a browser. Static assets live in `docs/_static/`.
