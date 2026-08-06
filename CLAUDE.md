# Releasing

```bash
uv run python bump_version_and_publish.py X.Y.Z
```

This updates the version in all four places (`VERSION`, `pyproject.toml`,
`tmsgpack/pyproject.toml`, `tmsgpack-js/package.json`), commits, tags
`vX.Y.Z`, and pushes. CI then publishes to PyPI and npm.
Do not bump the version or push unless the user asks.

