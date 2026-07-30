[[dictdefault]]
# `dictdefault`: get-or-create for plain dicts, in four variants

* Four variants of get-or-create for plain dicts (sync/async × with/without key).
* An alternative to `defaultdict` with explicit control.
* Async variants store a task, so the computation runs exactly once under concurrency.
* A failure is cached by the async variants and not by the sync ones.


```python
from semifun_caching.dictdefault import dictdefault

# Sync, factory receives no arguments:
value = dictdefault(cache, 'key', lambda: compute())

# Sync, factory receives the key:
value = dictdefault.k(cache, 'key', lambda k: compute(k))

# Async, factory receives no arguments:
value = await dictdefault.a(cache, 'key', lambda: async_compute())

# Async, factory receives the key:
value = await dictdefault.ak(cache, 'key', lambda k: async_compute(k))
```

## A failed computation

The sync variants assign the result, so a factory that raises leaves the cache
untouched and the next call recomputes.

The async variants store the *task* before it runs, and a failed task keeps its
exception.  The failure is therefore cached: every later caller awaits the same
task and gets the same exception, and the factory is never called again.

```python
await dictdefault.a(cache, 'key', failing)   # raises, and stores the failure
await dictdefault.a(cache, 'key', failing)   # raises again, without calling it
```

To retry, drop the key.
