[[di-inside-di]]
# DI inside DI: request the injector itself to make nested calls

* Continue dependency injection inside an injector with `Inject[DependencyInjector]` — typically with modified seed data.


```python
from semifun_dependency_injection.injector import DependencyInjector

async def outer(*, di: Inject[DependencyInjector], zctx: Inject[ZCtx]):
    # The injected `di` carries the same injectors and seed data as the current call.
    result = await di.async_call_with_args(fn=inner_fn, args=(), kwargs={})
    # with_seed_data merges: new keys are added, existing keys are overridden.
    result = await di.with_seed_data({ExtraType: value}).async_call_with_args(fn=other_fn, args=(), kwargs={})
```
