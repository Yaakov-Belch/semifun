"""Build, read, and write the per-package feature_plugins_index.json."""

import json
from pathlib import Path

from .model import IndexedFile, FeaturePluginsIndex
from .scanner import scan_package, build_indexed_file

INDEX_FILENAME = 'feature_plugins_index.json'


def build_index(package_path: Path) -> dict[str, list[str]]:
    """Scan a package and return the raw index data."""
    return scan_package(package_path)


def write_index(package_path: Path, index_data: dict[str, list[str]]):
    """Write the index to the package's feature_plugins_index.json."""
    index_file = package_path / INDEX_FILENAME
    index_file.write_text(json.dumps(index_data, indent=2, sort_keys=True) + '\n')


def read_index(package_path: Path) -> dict[str, list[str]] | None:
    """Read the cached index. Returns None if no cache file exists."""
    index_file = package_path / INDEX_FILENAME
    if not index_file.exists():
        return None
    return json.loads(index_file.read_text())


def get_index(package_path: Path, create_disk_cache: bool = False) -> dict[str, list[str]]:   # hidden-feature
    """Get a package's feature index: from its disk cache if present, else by scanning.

    hidden-feature: `create_disk_cache=True` scans the package and writes
    `feature_plugins_index.json` into the package directory.

    **Why it exists.**  Resolving a feature normally means scanning every
    source file of every participating package for `#::` comments, on every
    process start.  For code that will not change again — a built distribution
    — that work can be done once and its result shipped with the code, so each
    later start reads one JSON file instead of walking the sources.

    **Who sets it.**  A packaging step, deliberately, against code that is
    about to be frozen.  Nothing at run time sets it — a caller looking up a feature
    should not have to answer a build-time question.

    **Caution.**  A written index is preferred over scanning and nothing
    invalidates it.  An index that outlives the code it describes will silently
    shadow the source: features that were added are missing, features that were
    removed are still offered.  Write one only for code that will not change
    afterwards.

    Escalate periodically: is this still wanted?
    """
    if not create_disk_cache:
        cached = read_index(package_path)
        if cached is not None:
            return cached
    index_data = build_index(package_path)
    if create_disk_cache:
        write_index(package_path, index_data)
    return index_data


def index_to_model(
    package_path: Path,
    index_data: dict[str, list[str]],
    default_package: str,
    entry_point_group: str | None,
    entry_point_name: str | None,
) -> list[IndexedFile]:
    """Convert raw index data into IndexedFile model objects.

    `entry_point_group` / `entry_point_name` are `None` for registries built
    from explicit paths rather than entry points; pass them explicitly.
    """
    return [
        build_indexed_file(
            package_path=package_path,
            relative_path=rel_path,
            comments=comments,
            default_package=default_package,
            entry_point_group=entry_point_group,
            entry_point_name=entry_point_name,
        )
        for rel_path, comments in index_data.items()
    ]
