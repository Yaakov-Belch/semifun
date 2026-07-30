[[di.sync_call_with_args]]
# `sync_call_with_args`: the same DI call, without `await`

* Synchronous dependency injection for non-async contexts.
* All injectors in the chain must also be synchronous.


Use `sync_call_with_args` when calling from a synchronous context — identical
interface, no `await`.

```python
di = get_injector('z_injector')
result = di.with_seed_data({ZCtx: zctx}).sync_call_with_args(
    fn=my_fn, args=(), kwargs={},
)
```
