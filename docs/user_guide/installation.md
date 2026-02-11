# Installation

## Requirements

- **Python:** 3.11 or newer.

## Base install

From source:

```bash
git clone https://github.com/gsbm/converge.git
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

   **Testing:** Unit tests (`tests/unit/`), integration tests (`tests/integration/`), and end-to-end tests (`tests/e2e/`) can be run together with `pytest tests/` or by directory. E2E tests include multi-agent discovery and pool, restart recovery, and chaos-style claim TTL. A minimal **performance benchmark** (task submit/claim/report throughput) is in `benchmarks/local_task_throughput.py`; run with `python benchmarks/local_task_throughput.py` (optional env: `N=200`). No CI gate for benchmarks; use to spot regressions or compare customizations.

## Upgrading

When a new version is released, check the changelog for config and API changes. Run your test suite after upgrading. New optional config keys and parameters are added in a backward-compatible way; breaking changes are limited to the public API of core modules and are documented in release notes.

## Versioning and compatibility

Converge follows **semantic versioning**. Breaking changes are limited to the public API of core modules (e.g. `converge.core`, `converge.network`, `converge.coordination`, `converge.runtime`). New optional config keys and new optional parameters may be added in minor releases; existing config and call sites remain valid. After upgrading, run your test suite and see the changelog for any migration notes.

## Building documentation

```bash
pip install -e ".[docs]"
cd docs && make html
```

Open `docs/_build/html/index.html` in a browser. Static assets live in `docs/_static/`.
