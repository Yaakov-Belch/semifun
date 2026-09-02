# Plugin and DI API reference

* Low-level APIs for working with feature maps and injectors directly.


## `get_cached_feature_map(plugin_type) -> FeatureMap`

- `feature_map(feature=name)` — returns the registered object. Raises `LookupError` if not found.
- `feature_map(feature=name, default=None)` — returns `default` instead of raising.
- `feature_map.feature_names_and_objects` — sorted tuple of `(name, object)` pairs.


## `get_injector(injector_type) -> DependencyInjector`

- `di.with_seed_data(seed_data)` — return a new DependencyInjector with `seed_data`.
  - `seed_data` is a dict mapping types to instances.
- `await di.async_call_with_args(fn, args, kwargs)` — call `fn` with DI, async.
- `di.sync_call_with_args(fn, args, kwargs)` — call `fn` with DI, sync.
  - All injectors must be sync.
  - Nested dependency injection (DI inside DI) must use `SyncExecutionContext` — see [[di-inside-di]].


## `signature_without_Inject(fn) -> inspect.Signature`

Returns the function's signature with `Inject[T]` parameters removed — the caller-facing interface. Used for CLI help text, MCP tool schema generation, API documentation.


## Sample code

```python
plugin_type = 'z_command'

feature_map = get_cached_feature_map(plugin_type)

for feature, fn in feature_map.feature_names_and_objects:
    sig = signature_without_Inject(fn)
    doc = inspect.cleandoc(fn.__doc__ or "(no description)")
    print(f"{feature}{sig}")
    print(textwrap.indent(doc, "    "))


feature = 'show_my_posts'

fn = feature_map(feature=feature, default=None)   # Undefined feature: return None
fn = feature_map(feature=feature)                 # Undefined feature: raise exception

seed_data = {MongoClient: db_client, UserId: user_id}
injector_type = plugin_type + '_inject'

di = get_injector(injector_type)
result = await di.with_seed_data(seed_data).async_call_with_args(
    fn=fn, args=args, kwargs=kwargs,
)

result = di.with_seed_data(seed_data).sync_call_with_args(
    fn=fn, args=args, kwargs=kwargs,
)
```


## Manual execution context: shared cache and cleanup across multiple calls

* Create an `AsyncExecutionContext` (for sync: `SyncExecutionContext`) to
  share cache and cleanup across multiple dependency injection invocations.

```python
from semifun.di.async_execution_context import AsyncExecutionContext

di = get_injector(injector_type).with_seed_data(seed_data)
ctx = AsyncExecutionContext(injector=di)
try:
    obj = await ctx.invoke_call_with_args(fn1, args=(), kwargs={})
    result = await ctx.invoke_call_with_args(fn2, args=args, kwargs=kwargs)
finally:
    await ctx._cleanup()
```

