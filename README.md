# yb-tools

Python utilities: caching, plugin discovery, dependency injection, and CLI dispatch.

This repo also contains **tmsgpack**, a typed MessagePack serializer with both
Python (Cython) and JavaScript implementations:

- `tmsgpack/` -- Python package (published to PyPI as `tmsgpack`)
- `tmsgpack-js/` -- JavaScript package (published to npm as `tmsgpack`)

Install the pure-Python tools with `pip install yb-tools`. To include tmsgpack,
use `pip install yb-tools[tmsgpack]` (requires a C compiler for Cython).


## Versioning

A single `VERSION` file at the repo root is the source of truth. The Python and
JavaScript tmsgpack packages carry the same version.

To bump all packages at once:

```bash
python bump_version_and_publish.py 0.2.0
```

This updates `VERSION`, both `pyproject.toml` files, and `tmsgpack-js/package.json`.
A test (`tests/test_version_sync.py`) asserts all four stay in sync.


## Publishing

The CI workflow (`.github/workflows/publish.yml`) publishes all three packages
when you push a `v*` tag. It uses trusted publishing (OIDC) through a GitHub
`release` environment -- no API keys in the repo.

The script commits, tags, and pushes in one step:

```bash
python bump_version_and_publish.py 0.2.0
```

This triggers three parallel CI jobs:

- **yb-tools** -- built and published to PyPI (wheel + sdist)
- **tmsgpack** -- published to PyPI as an sdist (users compile Cython on install)
- **tmsgpack-js** -- published to npm with provenance

Before the first publish, configure trusted publishers on PyPI and npm for the
`Yaakov-Belch/yb-tools` repository, and create a `release` environment in the
GitHub repo settings.


## Development

The repo uses a [uv workspace](https://docs.astral.sh/uv/concepts/workspaces/)
so that `tmsgpack` resolves `yb-tools` locally during development.

```bash
git clone https://github.com/Yaakov-Belch/yb-tools.git
cd yb-tools
uv sync
```

Run the tests:

```bash
# yb-tools (pure Python)
uv run pytest tests/

# tmsgpack (requires Cython build)
cd tmsgpack && uv run pytest tests/

# tmsgpack-js
node tmsgpack-js/test/test.js
```
