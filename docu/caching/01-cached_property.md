[[cached-property-sync-and-async]]
# Cached properties with sync and async support

* Straight-forward code
* Consistency and edge cases


```python
from semifun_caching.cached_property import cached_property

@dataclass(frozen=True)
class Service:
    db_url: str

    @cached_property
    def config(self) -> dict:
        return load_config(self.db_url)

    @cached_property
    async def db(self) -> DbConnection:
        return await connect(self.db_url)

svc = Service(db_url='mongodb://localhost/mydb')
cfg = svc.config       # computed on first access, cached
cfg2 = svc.config      # same cached result

conn = await svc.db    # task created on first access, awaited here
conn2 = await svc.db   # same cached result, no recomputation
```

## Consistency and edge cases

When one async cached property is requested multiple times while it is computed,
all requests await the same awaitable and receive the same result -- computed once.
This is a reliable pattern to ensure one async operation is performed exactly once.

When async cached properties form a cycle, a `ValueError('Deadlock: ...')` is raised.
