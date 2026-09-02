# Nested dependency injection (DI inside DI)

Inject the execution context to make nested DI calls that share the same resolution cache — injected types resolve to the same instances.

```python
from semifun.di.async_execution_context import AsyncExecutionContext

async def combined_feature(*, ctx: Inject[AsyncExecutionContext], zctx: Inject[ZCtx]):
    # Run two functions with the same dependency injection context and cache:
    result1 = await ctx.invoke_call_with_args(fn_feature1, args=(), kwargs={})
    result2 = await ctx.invoke_call_with_args(fn_feature2, args=(), kwargs={})
```

When the top-level DI call is synchronous (`sync_call_with_args`), use `SyncExecutionContext`:

```python
from semifun.di.sync_execution_context import SyncExecutionContext

def combined_feature(*, ctx: Inject[SyncExecutionContext], zctx: Inject[ZCtx]):
    result1 = ctx.invoke_call_with_args(fn_feature1, args=(), kwargs={})
    result2 = ctx.invoke_call_with_args(fn_feature2, args=(), kwargs={})
```
