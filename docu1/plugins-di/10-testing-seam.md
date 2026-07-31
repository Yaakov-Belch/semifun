[[feature_map:testing-seam]]
# Testing seam: pass a callable where a feature-type string goes — tests only

* For tests only.  Production code always passes a `str`.
* `get_cached_feature_map` returns a callable argument unchanged, so a hand-built
  feature map replaces the scanned registry.
* `get_injector` inherits the seam: a callable becomes the `injectors_map` directly.
* The `str` annotation is a deliberate, test-only lie — controlled monkey-patching.


Tests need a command table without scanning packages, writing `#::` comments,
or registering entry points.  The seam provides it: wherever an API takes a
feature-type string, a test may pass a callable instead, and it is used as the
feature map.

```python
# A feature map is anything callable as lookup(feature, default) that also
# offers .feature_names and .feature_names_and_objects.
cli_map = MyFakeMap({'greet': greet_fn})

def injectors_map(name, default):
    return default          # no injectors: Inject[T] must come from seed_data

# Production: both arguments are strings.
await cli_dispatch_engine(
    cli_feature_type='cli',
    injector_feature_type='cli_inject',
    argv=argv,
    seed_data={},
)

# Test: both arguments are callables, through the seam.
await cli_dispatch_engine(
    cli_feature_type=cli_map,
    injector_feature_type=injectors_map,
    argv=['greet', 'name=Alice'],
    seed_data={},
)
```

The seam is one branch at the top of `get_cached_feature_map`:

```python
if callable(feature_type):  # testing-seam: allow passing a pre-built feature map
    return feature_type
```

`get_injector` needs no branch of its own — it builds
`DependencyInjector(injectors_map=get_cached_feature_map(feature_type=x))`, so
a callable `x` arrives as the `injectors_map`.

## Why the annotation says `str`

`get_cached_feature_map(feature_type: str, ...)` and
`get_injector(feature_type: str)` are annotated `str` because that is the only
type production code ever passes.  A test passing a callable is not a gap in
the type — it is monkey-patching, done through a declared entry point instead
of by reassigning module attributes.  The lie is intentional and confined to
tests: it stays out of production code, it is visible at the call site, and it
is narrower than `monkeypatch.setattr`, which replaces a name for every caller
in the process.

Prefer this seam over `monkeypatch`.  Patching module attributes also patches
them for code under test that you did not mean to touch, and it hides which
dependency the test is actually replacing.

## When a real registry is needed instead

For tests that must exercise scanning itself — `#::` comment parsing,
specificity rules, cross-package discovery — build a real registry from paths:

```python
from semifun_plugins.testing import create_registry_from_paths

registry = create_registry_from_paths(
    packages=[('my_pkg', tmp_path / 'my_pkg')],
)
```

Note that `get_cached_registry`, `get_cached_feature_map` and `get_injector`
are `@cache`d for the life of the process and nothing clears them.  Two tests
that build different registries for the *same* feature-type string will share
whichever was built first.  The seam avoids this by construction — distinct
callables are distinct cache keys — but `create_registry_from_paths`
does not, so keep such registries local to the test that builds them.
