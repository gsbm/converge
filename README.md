# converge

> A distributed operating system for agents

`converge` provides the foundational substrate for multi-agent computation: discovery, coordination, and execution so that networks of autonomous agents can operate without central control. It includes core primitives (identity, messages, tasks, pools), transport layers (local and TCP), policy and observability hooks, and an optional file-backed store. **This project is experimental; use at your own risk.**

## Table of Contents

- [Installation](#installation)
    - [From Source](#from-source)
    - [Development](#development)
- [Documentation](#documentation)
- [License](#license)

## Installation

### From Source

For the latest version:

```bash
git clone https://github.com/gsbm/converge.git
cd converge
pip install -e .
```

### Development

To set up the development environment with test and tooling dependencies:

```bash
git clone https://github.com/gsbm/converge.git
cd converge
pip install -e ".[dev]"
pre-commit install
```

Run tests with:

```bash
pytest -v
```

Optionally use `pytest -v --tb=short` for shorter tracebacks. For coverage (target 98%+; TCP tests require network):

```bash
coverage run -m pytest tests/
coverage report -m --fail-under=98
```

## Documentation

Library documentation is built with [Sphinx](https://www.sphinx-doc.org/) and written in Markdown. To build locally:

```bash
pip install -e ".[docs]"
cd docs && make html
```

Then open `docs/_build/html/index.html` in a browser. Static assets go in `docs/_static/`. See the [documentation index](docs/index.md) for structure and layout.

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.
