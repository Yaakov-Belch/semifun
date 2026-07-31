[[di-inside-di]]
# DI inside DI: nested calls within the same context or with a new one

Two options, depending on whether you want to share the resolution cache:

## Shared context: `Inject[AsyncExecutionContext]`

* The nested call shares the same cache — injected types resolve to the same instances.
* Use when multiple functions must see the same stateful object (e.g. `ReqReply`).

```python
from semifun.di.async_execution_context import AsyncExecutionContext

async def outer(*, ctx: Inject[AsyncExecutionContext], zctx: Inject[ZCtx]):
    # Nested call shares the cache: same Inject[T] values as outer.
    result = await ctx.invoke_call_with_args(inner_fn, args=(), kwargs={})
```

## Isolated context: `Inject[DependencyInjector]`

* The nested call gets a fresh cache — injected types are resolved independently.
* Use when you need modified seed data or intentional isolation.

```python
from semifun.di.injector import DependencyInjector

async def outer(*, di: Inject[DependencyInjector], zctx: Inject[ZCtx]):
    # Fresh context: inner_fn gets its own Inject[T] resolutions.
    result = await di.async_call_with_args(fn=inner_fn, args=(), kwargs={})
    # with_seed_data merges: new keys are added, existing keys are overridden.
    result = await di.with_seed_data({ExtraType: value}).async_call_with_args(fn=other_fn, args=(), kwargs={})
```
