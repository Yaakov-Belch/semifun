# Testing seam: bypass the registry

Pass a callable where a `plugin_type` string goes. The callable is used as the feature map directly — no scanning, no `#::` comments, no entry points.

```python
# A fake map must be callable as map(feature, default) and expose .feature_names_and_objects
cli_map = MyFakeMap({'greet': greet_fn})

# Production: plugin_type is a string
await cli_dispatch_engine(feature_type='cli', argv=argv, extra_kwargs=None, seed_data={}, help_output=print)

# Test: plugin_type is a callable — used as the feature map directly
await cli_dispatch_engine(
    feature_type=cli_map,
    argv=['greet', 'name=Alice'],
    extra_kwargs=None,
    seed_data={},
    help_output=print,
)
```

The seam is one branch in `get_cached_feature_map`:

```python
if callable(feature_type):
    return feature_type
```

`get_injector` inherits the seam — it builds its injector map via `get_cached_feature_map`, so a callable passes through.

Prefer this over `monkeypatch`. Module-level patching affects all callers in the process and hides which dependency the test replaces. The seam is visible at the call site and scoped to the call.
