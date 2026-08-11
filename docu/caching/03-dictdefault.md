[[dictdefault]]
# `dictdefault`: "defaultdict on plain dicts", sync/async and key support

* Choose: sync/async
* Choose: Constructor may or may not receive the key
* Design details


```python
from semifun_caching.dictdefault import dictdefault
sync_cache = {}; async_cache = {}   # sync/async: incompatible cache formats

# Sync, factory receives no arguments:
value = dictdefault(sync_cache, 'key', lambda: compute())

# Sync, factory receives the key:
value = dictdefault.k(sync_cache, 'key', lambda k: compute(k))

# Async, factory receives no arguments:
value = await dictdefault.a(async_cache, 'key', lambda: async_compute())

# Async, factory receives the key:
value = await dictdefault.ak(async_cache, 'key', lambda k: async_compute(k))
```

## Design details

* Multiple async requests for the same key while the first computation runs await the same result.  Computed only once.
* Computation loops:
  - Sync: `RecursionError` (standard Python recursion limit).
  - Async: `ValueError('Deadlock: ...')` (cycle detected via parent-task chain).
* Exceptions raised by the factory:
  - Sync: cache untouched, next call recomputes.
  - Async: failure is cached (task stores the exception), every later caller gets the same exception.  To retry, delete the key.
