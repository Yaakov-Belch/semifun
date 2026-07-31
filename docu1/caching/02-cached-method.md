[[cached-method]]
# `cached_method`: results keyed by a content hash of the call arguments

* Cache method results keyed by hashed arguments.
* The instance must have a `cache_codec` attribute (typically a `TmsgpackCodec`) providing `hash_to_bytes()`.
* Works on frozen dataclasses; async methods run exactly once under concurrency.
* Equivalent calls spelled differently share one cache entry.


```python
@dataclass(frozen=True)
class Repo:
    cache_codec: TmsgpackCodec

    @cached_method
    async def get_item(self, item_id: str) -> Item:
        return await self.db.fetch(item_id)

repo = Repo(cache_codec=TmsgpackCodec(...))   # see [[tmsgpack]] for the full construction
item = await repo.get_item('abc')    # computed and cached
same = await repo.get_item('abc')    # cache hit
other = await repo.get_item('xyz')   # different key, computed
```

The per-method cache dict is stored via `object.__setattr__`, so frozen
dataclasses work.  Async methods use `dictdefault.a` internally to ensure
once-only execution under concurrent access.

## Equivalent calls key the same

Arguments are bound to the signature and defaults applied before hashing, so
one call spelled three ways is computed once:

```python
@cached_method
async def get_page(self, item_id: str, limit: int = 10) -> Page: ...

await repo.get_page('abc')             # omitted
await repo.get_page('abc', 10)         # positional     -- one cache entry
await repo.get_page('abc', limit=10)   # keyword
```

The key is built from the *bound* arguments, so positional, keyword and
omitted-with-a-default spellings all normalise to the same entry.
