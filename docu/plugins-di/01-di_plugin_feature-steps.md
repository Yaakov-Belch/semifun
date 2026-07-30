[[di_plugin_feature:steps]]
# `di_plugin_feature`: look up a feature, inject, and call

```python
async def di_plugin_feature(
    *,
    plugin_type: str,
    feature: str,
    args: tuple = (),
    kwargs: dict[str, Any] | None = None,
    injector_type: str,
    seed_data: dict[type, Any],
) -> Any:
    feature_map = get_cached_feature_map(plugin_type)
    fn = feature_map(feature=feature)
    di = get_injector(injector_type)
    return await di.with_seed_data(seed_data).async_call_with_args(
        fn=fn, args=args, kwargs=kwargs or {},
    )
```
