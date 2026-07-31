[[plugins:testing-support]]
# `semifun_plugins.testing`: build a registry from paths, check every feature imports

* Public interface, used only by tests — production code does not import it.
* `create_registry_from_paths` builds a registry without installation or entry points.
* `load_all_features` proves every `#::` declaration resolves to a real object.
* For a command table with no scanning at all, prefer [[feature_map:testing-seam]].


A package that declares features with `#::` comments needs two things from its
tests: a registry it can build without installing anything, and a check that
every declaration actually resolves.  Both live in `semifun_plugins.testing`.

## A registry from explicit paths

```python
from semifun_plugins.testing import create_registry_from_paths

registry = create_registry_from_paths(
    packages=[('my_pkg', tmp_path / 'my_pkg')],
)
```

Each package's parent directory is added to `sys.path`, so the package becomes
importable by name — the same thing installation provides in production.

Use this when the test needs scanning itself to happen: `#::` comment parsing,
specificity rules, cross-package discovery.  When the test only needs a
command table, [[feature_map:testing-seam]] is lighter and avoids the
process-global caches.

To feed such a registry to an API that takes a feature type, convert it:

```python
from semifun_plugins.testing import feature_map_from_registry

cli_map = feature_map_from_registry(registry, feature_type='cli')
```

The result is a feature map, so it passes through the seam unchanged.  This is
how a test drives real code end to end — real `#::` declarations, real
discovery, real dispatch — without installing anything.

## Checking that declarations resolve

```python
from semifun_plugins.testing import get_feature_types, load_all_features

types = get_feature_types(registry)                      # ['cli', 'reader', ...]
features = load_all_features(registry, feature_types=None)   # None = all types
```

`load_all_features` imports every declared feature and raises if any source
file is missing, fails to import, or names an object that does not exist.  A
package with `#::` declarations should have one test that calls it: a typo in
a structured comment is otherwise invisible until the feature is first used.

## Why it is public

Test helpers that other packages need are part of the interface, not private
details — `semifun-cli-dispatch` and `tmsgpack` both build registries this way
for their own tests.  A helper reached through a leading underscore is being
used across a boundary it claims not to have.
