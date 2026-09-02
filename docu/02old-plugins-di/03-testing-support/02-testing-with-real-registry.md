# Testing with a real registry

When the test needs real `#::` scanning — comment parsing, cross-package discovery — build a registry from paths without installing anything.

```python
from semifun.plugins.testing import create_registry_from_paths, feature_map_from_registry

# Each package's parent directory is added to sys.path, so it becomes importable without installation.
registry = create_registry_from_paths(
    packages=[('my_pkg', tmp_path / 'my_pkg')],
)

# Convert to a feature map — passes through the testing seam unchanged
cli_map = feature_map_from_registry(registry, feature_type='cli')
```

**Validate that all `#::` declarations resolve** — catches typos in structured comments that are otherwise invisible until first use:

```python
from semifun.plugins.testing import get_feature_types, load_all_features

types = get_feature_types(registry)                        # ['cli', 'reader', ...]
features = load_all_features(registry, feature_types=None) # None = all types
```

**Caching caveat:** `get_cached_feature_map` and `get_injector` are `@cache`d for the process lifetime. Two tests building different registries for the same `plugin_type` string share whichever was built first. The testing seam avoids this — distinct callables are distinct cache keys.
