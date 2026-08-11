[[cached-method]]
# cached_method with sync and async support

* Straight-forward code, sync and async supported
* Design details


```python
from semifun_caching.cached_method import cached_method
from tmsgpack.codec import NoDependencyInjector, TmsgpackCodec

@dataclass(frozen=True)
class Repo:
    cache_codec: TmsgpackCodec

    @cached_method
    async def get_page(self, collection: str, page: int = 0, limit: int = 10) -> list:
        return await self.db.find(collection, skip=page * limit, limit=limit)

codec = TmsgpackCodec(sort_keys=True, di=NoDependencyInjector(), plugin_feature_type='tmsgpack_codec')
repo = Repo(cache_codec=codec)

items = await repo.get_page('posts')              # computed and cached
same1 = await repo.get_page('posts', 0, 10)       # cache hit — same bound arguments
same2 = await repo.get_page('posts', 0, limit=10) # cache hit — same bound arguments
other = await repo.get_page('posts', page=1)      # different key, computed
```

## Design details

* Sync and async methods are supported
* Cache keyed by `self.cache_codec.hash_to_bytes(bound_args)`.
  - Arguments are bound to the signature with defaults applied before hashing.
  - Equivalent arguments compute the same hash key.
* Multiple requests for the same computation while the first computation runs await
  the same result.  Computed only once.
* Computation loops:
  - Sync: `RecursionError` (standard Python recursion limit).
  - Async: `ValueError('Deadlock: ...')` (cycle detected via parent-task chain).
