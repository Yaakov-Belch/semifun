"""Create immutable registries from installed packages or explicit paths."""

import importlib.util
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from yb_tools.caching.cached_property import cached_property

from .model import FeaturePluginsIndex, FeatureMatches, FeatureMatch
from .index import get_index, index_to_model

DEFAULT_OPT_IN_GROUP = 'feature_plugins.default'


def _find_package_path(package_name: str) -> Path:
    """Find the filesystem path of a Python package."""
    spec = importlib.util.find_spec(package_name)
    if spec is None or spec.submodule_search_locations is None:
        raise ImportError(f"Package not found: {package_name}")
    return Path(spec.submodule_search_locations[0])


def create_registry(
    create_disk_cache: bool = False,     # hidden-feature
) -> FeaturePluginsIndex:
    """Create an immutable registry from installed packages.

    Discovers participating packages via the `DEFAULT_OPT_IN_GROUP` entry-point
    group, reads or builds the index for each, and combines them.

    hidden-feature: `create_disk_cache=True` writes each package's index to
    disk, so that a frozen distribution can skip scanning at every start.  Set
    by a packaging step, never at run time — see `get_index`, which explains
    the flag and its hazard.

    Escalate periodically: is this still wanted?
    """
    from importlib.metadata import entry_points
    all_indexed = []
    for ep in entry_points(group=DEFAULT_OPT_IN_GROUP):
        package_name = ep.value
        package_path = _find_package_path(package_name)
        index_data = get_index(package_path, create_disk_cache=create_disk_cache)
        indexed_files = index_to_model(
            package_path=package_path,
            index_data=index_data,
            default_package=package_name,
            entry_point_group=DEFAULT_OPT_IN_GROUP,
            entry_point_name=ep.name,
        )
        all_indexed.extend(indexed_files)
    return FeaturePluginsIndex(indexed_files=tuple(all_indexed))


# --- Cached convenience functions ---

@cache
def get_cached_registry() -> FeaturePluginsIndex:
    """The registry of every installed participating package, built once."""
    return create_registry(create_disk_cache=False)


_MISSING = object()


@dataclass(frozen=True, eq=False)
class FeatureMap:
    """Callable lookup for single-definition features of a given type.

    Identity semantics (eq=False): FeatureMaps are cached singletons, so
    identity comparison is correct. This also makes them hashable, which is
    needed because get_cached_feature_map has a testing seam that accepts a
    pre-built FeatureMap in place of a string — and @cache must hash its args.
    """
    by_name: dict[str, FeatureMatch]
    feature_type: str

    def __call__(self, feature: str, default=_MISSING):   # documented-default
        """Look up a feature by name.

        documented-default: omitting `default` is not a shortcut for
        `default=None` — it selects a different behaviour, raising
        `LookupError` instead of returning a value.  `None` is itself a
        legitimate default, so the two cases cannot share a spelling.
        """
        match = self.by_name.get(feature)
        if match is not None:
            return match.loaded_object
        if default is not _MISSING:
            return default
        raise LookupError(
            f"No '{self.feature_type}' feature named '{feature}'. "
            f"Available: {list(self.feature_names)}"
        )

    @cached_property
    def feature_names(self) -> tuple[str, ...]:
        return tuple(sorted(self.by_name.keys()))

    @cached_property
    def feature_names_and_objects(self) -> tuple[tuple[str, object], ...]:
        return tuple(
            (name, self.by_name[name].loaded_object)
            for name in self.feature_names
        )


def _feature_map_from_registry(
    registry: FeaturePluginsIndex,
    feature_type: str,
) -> FeatureMap:
    by_name = registry.find_features(
        feature_type=feature_type, feature_name=None, feature_package=None,
    ).by_name
    return FeatureMap(by_name=by_name, feature_type=feature_type)


@cache
def get_cached_feature_map(feature_type: str):
    """Cached feature lookup function for single-definition features.

    Returns a callable: lookup(feature_name, default=_MISSING) -> loaded object.

    Args:
        feature_type: The feature type to look up (e.g., 'reader', 'writer', 'cli').
            See [[feature_map:testing-seam]] for the callable form used by tests.
    """
    if callable(feature_type):  # testing-seam: allow passing a pre-built feature map
        return feature_type
    registry = get_cached_registry()
    return _feature_map_from_registry(registry, feature_type)
