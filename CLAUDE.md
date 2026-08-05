# CLAUDE.md — semifun

## Running commands

Always use `uv run` for Python commands — never bare `python` or `pytest`.
This project is often opened from a parent project's venv, and `uv run`
ignores the inherited `VIRTUAL_ENV`, using the project-local `.venv` instead.

```bash
uv run pytest                         # all tests
uv run pytest tests/cli/test_dispatch.py -x   # one file
uv run python -c "..."                # one-off scripts
```

## Project structure

- `src/semifun/` — library source (editable install via `uv`)
  - `caching/` — cached_property, cached_method, dictdefault
  - `cli/` — CLI dispatch, argv parsing, type casting
  - `di/` — dependency injection (async & sync), `Inject[T]` model
  - `plugins/` — plugin registry, scanner, feature maps
- `tmsgpack/` — workspace member: typed msgpack codec (Cython)
- `tests/` — mirrors `src/semifun/` layout
- `docu/` — documentation by subsystem

## Testing

```bash
uv run pytest              # run all tests
uv run pytest -x --tb=short   # stop on first failure
```

Tests use `pytest-asyncio` (mode=auto) and `pytest-timeout` (60s default).

## Releasing

```bash
uv run python bump_version_and_publish.py X.Y.Z
```

This updates the version in all four places (`VERSION`, `pyproject.toml`,
`tmsgpack/pyproject.toml`, `tmsgpack-js/package.json`), commits, tags
`vX.Y.Z`, and pushes. CI then publishes to PyPI and npm.
Do not bump the version or push unless the user asks.

## Key conventions

- `Inject[T]` (PEP 695 type alias) marks DI-injected parameters.
  Use `injected_type(annotation)` from `semifun.di.model` to detect it
  (not `__origin__`; it's a type alias, so use `typing.get_origin`).
- Plugin annotations: `#::feature_type:feature_name` comments in source.
- Injector naming convention: injector type = `{plugin_type}_inject`.
