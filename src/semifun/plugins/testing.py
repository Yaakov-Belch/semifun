"""Test support: build registries from paths, and verify that features import.

This module is part of the public interface.  Tests in this package, and in
any package that discovers features through `semifun-plugins`, use it to build
a registry without installing anything or declaring entry points.

Production code does not import from here.

See [[plugins:testing-support]] and [[feature_map:testing-seam]] — for a
command table with no scanning at all, prefer the seam.
"""

import sys
from dataclasses import dataclass
from pathlib import Path

from .index import get_index, index_to_model
from .model import FeaturePluginsIndex
from .registry import FeatureMap, _feature_map_from_registry


def create_registry_from_paths(
    packages: list[tuple[str, Path]],
) -> FeaturePluginsIndex:
    """Create an immutable registry from explicit paths.

    Each package's parent directory is added to `sys.path` so the package is
    importable by its name.  This mirrors what installation provides in
    production: a package reachable via `importlib.import_module(name)`.

    Args:
        packages: List of (package_name, package_path) tuples.
    """
    all_indexed = []
    for package_name, package_path in packages:
        parent = str(package_path.parent)
        if parent not in sys.path:
            sys.path.insert(0, parent)
        index_data = get_index(package_path, create_disk_cache=False)
        indexed_files = index_to_model(
            package_path=package_path,
            index_data=index_data,
            default_package=package_name,
            entry_point_group=None,   # built from paths, not from an entry point
            entry_point_name=None,
        )
        all_indexed.extend(indexed_files)
    return FeaturePluginsIndex(indexed_files=tuple(all_indexed))


def feature_map_from_registry(
    registry: FeaturePluginsIndex,
    feature_type: str,
) -> FeatureMap:
    """Return the feature map of one feature type, for a registry built here.

    Production code reaches a feature map through `get_cached_feature_map`,
    which consults the installed packages.  A test that scanned its own
    packages with `create_registry_from_paths` needs the same conversion
    without that lookup; the result can be handed straight to any API taking a
    feature type, per [[feature_map:testing-seam]].
    """
    return _feature_map_from_registry(registry, feature_type)


@dataclass(frozen=True)
class LoadedFeature:
    """A feature that has been discovered and successfully imported."""
    feature_type: str
    name: str
    object: object


def get_feature_types(registry: FeaturePluginsIndex) -> list[str]:
    """Return a sorted list of all distinct feature types in the registry."""
    return sorted({m.feature_spec.feature_type for m in registry._all_matches})


def load_all_features(
    registry: FeaturePluginsIndex,
    feature_types: list[str] | None,
) -> list[LoadedFeature]:
    """Load all declared features and return them as LoadedFeature objects.

    This verifies that every declared feature can be imported successfully.
    If any feature's source file is missing, has import errors, or declares a
    function/class name that does not exist, this raises.

    Args:
        registry: The plugin registry to inspect.
        feature_types: Only load features of these types.  `None` loads all —
            a meaningful value, passed explicitly.

    Returns:
        Sorted list of LoadedFeature(feature_type, name, object).
    """
    if feature_types is None:
        feature_types = get_feature_types(registry)

    results = []
    for ft in feature_types:
        by_name = registry.find_features(
            feature_type=ft, feature_name=None, feature_package=None,
        ).by_name
        for name, match in by_name.items():
            results.append(LoadedFeature(
                feature_type=ft,
                name=name,
                object=match.loaded_object,
            ))
    return sorted(results, key=lambda r: (r.feature_type, r.name))
