from semifun.plugins.registry import get_cached_feature_map
from semifun.di.registry_integration import get_injector


async def run_all_plugins(*, plugin_type, seed_data):
    injector_type = plugin_type + '_inject'
    feature_map = get_cached_feature_map(plugin_type)
    di = get_injector(injector_type).with_seed_data(seed_data)
    return [
        await di.async_call_with_args(fn=fn, args=(), kwargs={})
        for name, fn in feature_map.feature_names_and_objects
    ]
