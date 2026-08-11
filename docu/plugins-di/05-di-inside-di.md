[[di-inside-di]]
# DI inside DI: nested calls within the same execution context

Inject the execution context to make nested DI calls that share the same
resolution cache — injected types resolve to the same instances.

Use when multiple functions must see the same stateful object (e.g. `ReqReply`).

```python
from semifun.di.async_execution_context import AsyncExecutionContext

async def outer(*, ctx: Inject[AsyncExecutionContext], zctx: Inject[ZCtx]):
    # Nested call shares the cache: same Inject[T] values as outer.
    result = await ctx.invoke_call_with_args(inner_fn, args=(), kwargs={})
```

When the top-level DI call is sync, use `SyncExecutionContext` with `invoke_call_with_args` (not awaited):

```python
from semifun.di.sync_execution_context import SyncExecutionContext

def outer(*, ctx: Inject[SyncExecutionContext], zctx: Inject[ZCtx]):
    result = ctx.invoke_call_with_args(inner_fn, args=(), kwargs={})
```
