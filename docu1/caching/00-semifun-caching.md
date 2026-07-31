[[semifun-caching]]
# Caching utilities: three primitives for frozen dataclasses and async code

* Three caching primitives for async-first, frozen-dataclass architectures.
* `cached_property` — compute once on first access (sync or async, with deadlock detection).
* `cached_method` — cache method results keyed by hashed arguments.
* `dictdefault` — caching dict accessor that ensures once-only computation.


```python
from semifun_caching.cached_property import cached_property
from semifun_caching.cached_method import cached_method
from semifun_caching.dictdefault import dictdefault

@dataclass(frozen=True)
class Config:
    db_url: str

    @cached_property
    async def connection(self) -> DbConnection:
        return await connect(self.db_url)

    @cached_method
    async def query(self, sql: str) -> list:
        conn = await self.connection
        return await conn.execute(sql)

# dictdefault: get-or-create in a plain dict
cache = {}
value = dictdefault(cache, 'key', lambda: expensive_computation())
```
