[[cached-property:async]]
# Async cached properties: task created on first access, deadlocks detected on await

* When the decorated function is a coroutine, the task is eagerly created on first attribute access.
* Awaiting checks for deadlocks — a self-referential chain of cached properties raises `ValueError('Deadlock: ...')`.
* Deadlock detection is part of async caching, not a separate feature.


```python
@dataclass(frozen=True)
class Service:
    @cached_property
    async def db(self) -> DbConnection:
        return await connect(self.db_url)

svc = Service()
conn = await svc.db    # task created on first access, awaited here
conn2 = await svc.db   # same cached result, no recomputation
```

## Why caching brings deadlock detection with it

Caching an async property means handing every caller the *same* awaitable.
That is what makes a cycle possible: a property that awaits itself, directly or
through another property, ends up awaiting the task it is already running in,
and would wait forever.

So the check is not an optional extra — it is the cost of caching the
awaitable.  Each task records the task that created it, and awaiting walks that
chain: reaching the task doing the awaiting means the cycle is closed, and
`ValueError('Deadlock: ...')` is raised instead of hanging.

Two waiters in separate tasks are not a cycle and do not raise.
