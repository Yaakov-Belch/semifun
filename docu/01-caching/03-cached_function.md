[[cached-async-function]]
# cached_async_function: cache a standalone async function by arguments

* Callable repeatedly — same `fn` + same `fn_cache` returns the same wrapper
* Two caches: `fn_cache` (wrapper identity), `result_cache` (computation results)
* Design details


```python
from semifun.caching.cached_function import cached_async_function
from tmsgpack.api import basic_codec

fn_cache = {}
result_cache = {}

async def compute_tree_spec(query, config, user_data):
    ...  # expensive or stateful computation

# Can be called repeatedly — returns the same wrapper from fn_cache:
cached_fn = cached_async_function(
    fn=compute_tree_spec,
    fn_cache=fn_cache, result_cache=result_cache, cache_codec=basic_codec,
)

spec1 = await cached_fn('[[specs]]', cfg, ud)        # computed and cached
spec2 = await cached_fn('[[specs]]', cfg, ud)        # cache hit — same arguments
spec3 = await cached_fn('[[specs]]', cfg, ud2)       # different user_data, computed
spec4 = await cached_fn('[[specs]]', changed_cfg, ud) # different config, computed
```

## Design details

* `fn_cache` caches the wrapper function itself, keyed by `fn`.
  `cached_async_function(fn, fn_cache, ...)` can be called on every request —
  `dictdefault(fn_cache, fn, wrap_fn)` returns the same wrapper each time.
* `result_cache` caches computation results, keyed by argument hash.
  `dictdefault.a(result_cache, key, ...)` handles async dedup — concurrent calls
  for the same key await the same computation.
* Cache keyed by `cache_codec.hash_to_bytes(bound_args)`.
  - Arguments are bound to the signature with defaults applied before hashing.
  - Equivalent arguments compute the same hash key.
* Async only (no sync variant).
