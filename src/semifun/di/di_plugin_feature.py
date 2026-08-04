from typing import Any

from semifun.plugins.registry import get_cached_feature_map
from semifun.di.registry_integration import get_injector


async def di_plugin_feature(
    *,
    plugin_type: str,
    feature: str,
    args: tuple,
    kwargs: dict[str, Any],
    seed_data: dict[type, Any],
) -> Any:
    feature_map = get_cached_feature_map(plugin_type)
    fn = feature_map(feature=feature)
    injector_type = plugin_type + '_inject'
    di = get_injector(injector_type)
    return await di.with_seed_data(seed_data).async_call_with_args(
        fn=fn, args=args, kwargs=kwargs,
    )
