"""Cached DependencyInjector factory using the feature plugins registry.

Requires the optional `registry` extra:
    pip install semifun-dependency-injection[registry]

Usage:
    from yb_tools.di.registry_integration import get_injector

    di = get_injector('xctx_injector')
    di = get_injector('di_injector')

Returns the same DependencyInjector instance for each feature_type (cached).
"""

from functools import cache

from yb_tools.plugins.registry import get_cached_feature_map
from .injector import DependencyInjector


@cache
def get_injector(feature_type: str) -> DependencyInjector:
    """Return a cached DependencyInjector for the given feature_type.

    The injectors_map is obtained from the feature plugins registry via
    get_cached_feature_map. Both the feature map and the DependencyInjector
    (with its signature caches) are cached for the lifetime of the process.
    """
    return DependencyInjector(injectors_map=get_cached_feature_map(feature_type=feature_type), seed_data={})
